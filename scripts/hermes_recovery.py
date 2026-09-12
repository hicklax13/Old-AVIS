#!/usr/bin/env python3
"""Encrypted, application-consistent recovery backups for Connor's Hermes host.

The scheduled backup path never reads the recovery identity.  It stages data in
a private local directory, snapshots SQLite databases through SQLite's backup
API, encrypts the resulting tarball to an age *recipient*, and publishes only
ciphertext plus a non-secret integrity sidecar.  Restore is deliberately an
isolated operation: it will not overwrite a live source tree.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import logging
import os
import re
import shutil
import sqlite3
import stat
import subprocess
import sys
import tarfile
import time
import uuid
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path, PurePosixPath
from typing import Any, Iterator, Sequence


REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from hermes_cli.backup import (  # noqa: E402
    BackupInProgressError,
    _backup_operation_lock,
    _safe_copy_db,
)
from hermes_security import (  # noqa: E402
    PrivatePathError,
    create_private_file,
    is_reparse_point,
    secure_private_directory,
    secure_private_path,
    verify_private_path,
    verify_private_tree,
)


def _lexical_absolute(path: Path) -> Path:
    """Return an absolute path without resolving Windows cloud reparse points.

    OneDrive Personal Vault paths can resolve to an internal ``VaultData``
    volume spelling that is not reopenable by ordinary Win32 callers.  The
    user-visible path is the stable access route, so identities deliberately
    use lexical absolutization rather than ``Path.resolve()``.
    """
    return Path(os.path.abspath(os.path.expanduser(os.fspath(path))))


LOGGER = logging.getLogger("hermes_recovery")
PLAN_VERSION = 1
SQLITE_HEADER = b"SQLite format 3\x00"
AGE_RECIPIENT_RE = re.compile(r"^age1[023456789acdefghjklmnpqrstuvwxyz]{20,}$")
ARCHIVE_RE = re.compile(
    r"^hermes-recovery-(?P<stamp>\d{8}T\d{6}Z)-(?P<run>[0-9a-f]{8})(?:-full)?\.tar\.gz\.age$"
)

# These trees are reproducible dependencies, caches, live browser stores, old
# backups, or the recovery system itself.  They are not recovery state.
COMMON_EXCLUDED_DIRS = frozenset(
    {
        ".git",
        ".cache",
        ".mypy_cache",
        ".nox",
        ".pytest_cache",
        ".ruff_cache",
        ".tox",
        ".venv",
        ".venv-repaired",
        "__pycache__",
        "backups",
        "bin",
        "browser-profile",
        "browser-profiles",
        "build",
        "cache",
        "checkpoints",
        "code cache",
        "dawngraphitecache",
        "dawnwebgpucache",
        "deps",
        "dist",
        "gpucache",
        "hermes-agent",
        "logs",
        "lsp",
        "node",
        "node_modules",
        "npm-runtime",
        "recovery",
        "release",
        "runtime",
        "sandboxes",
        "services",
        "site-packages",
        "state-snapshots",
        "tmp",
        "tools",
        "tts",
        "venv",
    }
)
COMMON_EXCLUDED_NAMES = frozenset(
    {
        ".backup.lock",
        ".ha_run.lock",
        ".mcp-discovery.lock",
        "auth.lock",
        "cron.pid",
        "devtoolsactiveport",
        "gateway.lock",
        "gateway.pid",
        "kanban.db.dispatch.lock",
        "kanban.db.init.lock",
        "lockfile",
        "processes.json",
    }
)
COMMON_EXCLUDED_SUFFIXES = (
    ".db-journal",
    ".db-shm",
    ".db-wal",
    ".journal",
    ".pyc",
    ".pyo",
    ".sqlite-journal",
    ".sqlite-shm",
    ".sqlite-wal",
)
DESKTOP_STABLE_NAMES = frozenset(
    {
        "active-profile.json",
        "backend-ownership.json",
        "connection.json",
        "connections.json",
        "desktop-installation.json",
        "disable-f12.json",
        "hud-state.json",
        "keep-awake.json",
        "secure-token-storage.json",
        "translucency.json",
        "window-state.json",
        "windows-sandbox-fallback.json",
        "zoom-state.json",
    }
)


class RecoveryError(RuntimeError):
    """The backup or restore could not satisfy its safety contract."""


@dataclass(frozen=True)
class Destination:
    path: Path
    retention: int
    required: bool
    private: bool


@dataclass(frozen=True)
class Source:
    name: str
    path: Path
    kind: str
    container: str | None
    full_only: bool


@dataclass(frozen=True)
class RecoveryPlan:
    path: Path
    age_executable: Path
    recipient: str
    hermes_home: Path
    staging_root: Path
    status_path: Path
    destinations: tuple[Destination, ...]
    sources: tuple[Source, ...]


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _iso_utc(value: datetime | None = None) -> str:
    return (value or _utc_now()).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _write_json_private(path: Path, value: Any) -> None:
    secure_private_directory(path.parent)
    temporary = path.with_name(f".{path.name}.{os.getpid()}-{uuid.uuid4().hex}.tmp")
    create_private_file(temporary)
    try:
        temporary.write_text(
            json.dumps(value, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        secure_private_path(temporary, directory=False)
        os.replace(temporary, path)
        secure_private_path(path, directory=False)
    finally:
        temporary.unlink(missing_ok=True)


def _require_absolute_path(raw: Any, label: str) -> Path:
    if not isinstance(raw, str) or not raw.strip():
        raise RecoveryError(f"{label} must be a non-empty absolute path")
    path = Path(raw).expanduser()
    if not path.is_absolute():
        raise RecoveryError(f"{label} must be absolute: {path}")
    return path


def load_plan(path: Path) -> RecoveryPlan:
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise RecoveryError(f"Could not read recovery plan {path}: {exc}") from exc
    if not isinstance(raw, dict) or raw.get("version") != PLAN_VERSION:
        raise RecoveryError(f"Recovery plan must use version {PLAN_VERSION}")
    allowed_plan_keys = {
        "age_executable",
        "destinations",
        "hermes_home",
        "recipient",
        "sources",
        "staging_root",
        "status_path",
        "version",
    }
    unknown_plan_keys = sorted(set(raw) - allowed_plan_keys)
    if unknown_plan_keys:
        raise RecoveryError(f"Unknown recovery-plan keys: {unknown_plan_keys}")
    forbidden_key_fragments = ("identity", "private_key", "passphrase", "password")
    serialized_keys = " ".join(str(key).casefold() for key in raw)
    if any(fragment in serialized_keys for fragment in forbidden_key_fragments):
        raise RecoveryError("A recovery plan may never contain a private identity or password")

    recipient = raw.get("recipient")
    if not isinstance(recipient, str) or not AGE_RECIPIENT_RE.fullmatch(recipient):
        raise RecoveryError("Recovery plan contains an invalid age recipient")

    destinations_raw = raw.get("destinations")
    if not isinstance(destinations_raw, list) or not destinations_raw:
        raise RecoveryError("Recovery plan needs at least one destination")
    destinations: list[Destination] = []
    seen_destinations: set[str] = set()
    for index, item in enumerate(destinations_raw):
        if not isinstance(item, dict):
            raise RecoveryError(f"destinations[{index}] must be an object")
        unknown = sorted(set(item) - {"path", "retention", "required", "private"})
        if unknown:
            raise RecoveryError(f"Unknown destinations[{index}] keys: {unknown}")
        destination_path = _require_absolute_path(item.get("path"), f"destinations[{index}].path")
        normalized = os.path.normcase(str(destination_path.resolve(strict=False)))
        if normalized in seen_destinations:
            raise RecoveryError(f"Duplicate recovery destination: {destination_path}")
        seen_destinations.add(normalized)
        retention = item.get("retention", 7)
        if not isinstance(retention, int) or retention < 2 or retention > 100:
            raise RecoveryError(f"destinations[{index}].retention must be between 2 and 100")
        destinations.append(
            Destination(
                path=destination_path,
                retention=retention,
                required=bool(item.get("required", True)),
                private=bool(item.get("private", False)),
            )
        )

    sources_raw = raw.get("sources")
    if not isinstance(sources_raw, list) or not sources_raw:
        raise RecoveryError("Recovery plan needs at least one source")
    sources: list[Source] = []
    seen_names: set[str] = set()
    for index, item in enumerate(sources_raw):
        if not isinstance(item, dict):
            raise RecoveryError(f"sources[{index}] must be an object")
        unknown = sorted(set(item) - {"name", "path", "kind", "container", "full_only"})
        if unknown:
            raise RecoveryError(f"Unknown sources[{index}] keys: {unknown}")
        name = item.get("name")
        if not isinstance(name, str) or not re.fullmatch(r"[a-z0-9][a-z0-9-]{1,63}", name):
            raise RecoveryError(f"sources[{index}].name is invalid")
        if name in seen_names:
            raise RecoveryError(f"Duplicate source name: {name}")
        seen_names.add(name)
        kind = item.get("kind", "tree")
        if kind not in {"tree", "desktop", "git-snapshot"}:
            raise RecoveryError(f"Unsupported source kind for {name}: {kind}")
        container = item.get("container")
        if container is not None and (
            not isinstance(container, str) or not re.fullmatch(r"[A-Za-z0-9_.-]+", container)
        ):
            raise RecoveryError(f"Invalid container name for {name}")
        sources.append(
            Source(
                name=name,
                path=_require_absolute_path(item.get("path"), f"source {name}.path"),
                kind=kind,
                container=container,
                full_only=bool(item.get("full_only", False)),
            )
        )

    plan = RecoveryPlan(
        path=path.resolve(),
        age_executable=_require_absolute_path(raw.get("age_executable"), "age_executable"),
        recipient=recipient,
        hermes_home=_require_absolute_path(raw.get("hermes_home"), "hermes_home"),
        staging_root=_require_absolute_path(raw.get("staging_root"), "staging_root"),
        status_path=_require_absolute_path(raw.get("status_path"), "status_path"),
        destinations=tuple(destinations),
        sources=tuple(sources),
    )
    _validate_plan_boundaries(plan)
    return plan


def _validate_plan_boundaries(plan: RecoveryPlan) -> None:
    if not plan.age_executable.is_file():
        raise RecoveryError(f"age executable is missing: {plan.age_executable}")
    if not plan.hermes_home.is_dir():
        raise RecoveryError(f"Hermes home is missing: {plan.hermes_home}")
    staging = plan.staging_root.resolve(strict=False)
    home = plan.hermes_home.resolve()
    if staging == home or home not in staging.parents:
        raise RecoveryError("staging_root must be a child of hermes_home")
    for source in plan.sources:
        if not source.path.exists():
            if source.full_only:
                continue
            raise RecoveryError(f"Required recovery source is missing: {source.name} ({source.path})")
        if is_reparse_point(source.path):
            raise RecoveryError(f"Recovery source may not be a reparse point: {source.path}")
    for destination in plan.destinations:
        resolved = destination.path.resolve(strict=False)
        if resolved == staging or staging in resolved.parents or resolved in staging.parents:
            raise RecoveryError(f"Destination overlaps staging_root: {destination.path}")


def _is_sqlite(path: Path) -> bool:
    try:
        if path.stat().st_size < len(SQLITE_HEADER):
            return False
        with path.open("rb") as handle:
            return handle.read(len(SQLITE_HEADER)) == SQLITE_HEADER
    except OSError:
        return False


def _sqlite_quick_check(path: Path) -> str:
    connection: sqlite3.Connection | None = None
    try:
        connection = sqlite3.connect(f"file:{path}?mode=ro", uri=True, timeout=5)
        row = connection.execute("PRAGMA quick_check").fetchone()
        result = str(row[0]) if row else "missing result"
    except sqlite3.Error as exc:
        raise RecoveryError(f"SQLite quick_check failed for {path}: {exc}") from exc
    finally:
        if connection is not None:
            connection.close()
    if result.lower() != "ok":
        raise RecoveryError(f"SQLite quick_check failed for {path}: {result}")
    return result


def _skip_file(name: str) -> bool:
    lowered = name.casefold()
    return (
        lowered in COMMON_EXCLUDED_NAMES
        or lowered.endswith(COMMON_EXCLUDED_SUFFIXES)
        or lowered.endswith((".log", ".lock", ".pid"))
        or ".log." in lowered
    )


def _copy_file_consistently(source: Path, destination: Path) -> dict[str, Any]:
    destination.parent.mkdir(parents=True, exist_ok=True)
    if _is_sqlite(source):
        if not _safe_copy_db(source, destination, timeout_seconds=30.0):
            raise RecoveryError(f"Could not create a consistent SQLite snapshot: {source}")
        _sqlite_quick_check(destination)
        kind = "sqlite-snapshot"
    else:
        shutil.copy2(source, destination)
        kind = "file-copy"
    return {"kind": kind, "bytes": destination.stat().st_size}


def _copy_tree(source: Path, destination: Path) -> dict[str, Any]:
    destination.mkdir(parents=True, exist_ok=True)
    files = 0
    bytes_copied = 0
    sqlite_files = 0
    skipped_reparse = 0
    for dirpath, dirnames, filenames in os.walk(source, topdown=True, followlinks=False):
        parent = Path(dirpath)
        relative_parent = parent.relative_to(source)
        retained: list[str] = []
        for name in dirnames:
            candidate = parent / name
            if name.casefold() in COMMON_EXCLUDED_DIRS or is_reparse_point(candidate):
                skipped_reparse += int(is_reparse_point(candidate))
                continue
            retained.append(name)
            (destination / relative_parent / name).mkdir(parents=True, exist_ok=True)
        dirnames[:] = retained
        for name in filenames:
            candidate = parent / name
            if _skip_file(name) or is_reparse_point(candidate):
                skipped_reparse += int(is_reparse_point(candidate))
                continue
            target = destination / relative_parent / name
            detail = _copy_file_consistently(candidate, target)
            files += 1
            bytes_copied += int(detail["bytes"])
            sqlite_files += int(detail["kind"] == "sqlite-snapshot")
    return {
        "files": files,
        "bytes": bytes_copied,
        "sqlite_snapshots": sqlite_files,
        "reparse_points_skipped": skipped_reparse,
    }


def _copy_desktop_state(source: Path, destination: Path) -> dict[str, Any]:
    destination.mkdir(parents=True, exist_ok=True)
    files = 0
    bytes_copied = 0
    for name in sorted(DESKTOP_STABLE_NAMES):
        candidate = source / name
        if candidate.is_file() and not is_reparse_point(candidate):
            detail = _copy_file_consistently(candidate, destination / name)
            files += 1
            bytes_copied += int(detail["bytes"])
    images = source / "composer-images"
    if images.is_dir() and not is_reparse_point(images):
        detail = _copy_tree(images, destination / "composer-images")
        files += int(detail["files"])
        bytes_copied += int(detail["bytes"])
    return {"files": files, "bytes": bytes_copied, "sqlite_snapshots": 0}


def _run_git(repo: Path, *args: str, binary: bool = False) -> bytes:
    completed = subprocess.run(
        ["git", "-C", str(repo), *args],
        check=False,
        capture_output=True,
    )
    if completed.returncode != 0:
        message = completed.stderr.decode("utf-8", errors="replace").strip()
        raise RecoveryError(f"git {' '.join(args)} failed: {message}")
    return completed.stdout if binary else completed.stdout.replace(b"\r\n", b"\n")


def _snapshot_repository(repo: Path, destination: Path) -> dict[str, Any]:
    if not (repo / ".git").exists():
        raise RecoveryError(f"Repository source is not a Git checkout: {repo}")
    destination.mkdir(parents=True, exist_ok=True)
    outputs = {
        "head.txt": _run_git(repo, "rev-parse", "HEAD"),
        "branch.txt": _run_git(repo, "branch", "--show-current"),
        "status.txt": _run_git(repo, "status", "--short", "--branch"),
        "refs.txt": _run_git(repo, "show-ref", "--head"),
        "working-tree.patch": _run_git(repo, "diff", "--binary", binary=True),
        "index.patch": _run_git(repo, "diff", "--binary", "--cached", binary=True),
    }
    files = 0
    bytes_copied = 0
    for name, content in outputs.items():
        target = destination / name
        target.write_bytes(content)
        files += 1
        bytes_copied += len(content)

    untracked_raw = _run_git(
        repo,
        "ls-files",
        "--others",
        "--exclude-standard",
        "-z",
        binary=True,
    )
    for raw_name in untracked_raw.split(b"\x00"):
        if not raw_name:
            continue
        relative_text = raw_name.decode("utf-8", errors="surrogateescape")
        relative = Path(relative_text)
        candidate = repo / relative
        if not candidate.is_file() or is_reparse_point(candidate):
            continue
        target = destination / "untracked" / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(candidate, target)
        files += 1
        bytes_copied += target.stat().st_size
    return {"files": files, "bytes": bytes_copied, "sqlite_snapshots": 0}


def _container_state(name: str) -> tuple[str, str]:
    completed = subprocess.run(
        [
            "docker",
            "inspect",
            "--format",
            "{{.State.Status}}|{{if .State.Health}}{{.State.Health.Status}}{{else}}none{{end}}",
            name,
        ],
        check=False,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    if completed.returncode != 0:
        raise RecoveryError(f"Could not inspect required container {name}")
    parts = completed.stdout.strip().split("|", 1)
    return parts[0], parts[1] if len(parts) > 1 else "none"


def _wait_for_container(name: str, timeout_seconds: float = 120.0) -> None:
    deadline = time.monotonic() + timeout_seconds
    last = ("unknown", "unknown")
    while time.monotonic() < deadline:
        last = _container_state(name)
        if last[0] == "running" and last[1] in {"healthy", "none"}:
            return
        if last[1] == "unhealthy" or last[0] in {"dead", "exited"}:
            break
        time.sleep(2)
    raise RecoveryError(f"Container did not recover after backup: {name} state={last}")


@contextmanager
def _paused_containers(names: Sequence[str]) -> Iterator[None]:
    started: list[str] = []
    primary_error: BaseException | None = None
    unique_names = list(dict.fromkeys(name for name in names if name))
    try:
        for name in unique_names:
            status, _ = _container_state(name)
            if status == "running":
                completed = subprocess.run(
                    ["docker", "stop", "--time", "30", name],
                    check=False,
                    capture_output=True,
                    text=True,
                )
                if completed.returncode != 0:
                    raise RecoveryError(f"Could not pause container {name} for backup")
                started.append(name)
        yield
    except BaseException as exc:
        primary_error = exc
        raise
    finally:
        restart_errors: list[str] = []
        for name in reversed(started):
            completed = subprocess.run(
                ["docker", "start", name],
                check=False,
                capture_output=True,
                text=True,
            )
            if completed.returncode != 0:
                restart_errors.append(f"{name}: start failed")
                continue
            try:
                _wait_for_container(name)
            except RecoveryError as exc:
                restart_errors.append(str(exc))
        if restart_errors and primary_error is None:
            raise RecoveryError("; ".join(restart_errors))


def _manifest_for_payload(
    payload: Path,
    *,
    run_id: str,
    started_at: str,
    completed_at: str,
    full: bool,
    source_records: list[dict[str, Any]],
) -> dict[str, Any]:
    files: list[dict[str, Any]] = []
    for path in sorted(candidate for candidate in payload.rglob("*") if candidate.is_file()):
        relative = path.relative_to(payload).as_posix()
        record: dict[str, Any] = {
            "path": relative,
            "bytes": path.stat().st_size,
            "sha256": _sha256(path),
        }
        if _is_sqlite(path):
            record["sqlite_quick_check"] = _sqlite_quick_check(path)
        files.append(record)
    return {
        "format": "hermes-encrypted-recovery",
        "version": 1,
        "run_id": run_id,
        "started_at": started_at,
        "completed_at": completed_at,
        "full": full,
        "source_records": source_records,
        "file_count": len(files),
        "total_bytes": sum(int(item["bytes"]) for item in files),
        "files": files,
    }


def _make_tar(stage: Path, output: Path) -> None:
    with tarfile.open(output, "w:gz", compresslevel=6) as archive:
        archive.add(stage / "manifest.json", arcname="manifest.json", recursive=False)
        archive.add(stage / "payload", arcname="payload", recursive=True)
    secure_private_path(output, directory=False)


def _encrypt(age_executable: Path, recipient: str, source: Path, destination: Path) -> None:
    destination.unlink(missing_ok=True)
    completed = subprocess.run(
        [str(age_executable), "--recipient", recipient, "--output", str(destination), str(source)],
        check=False,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    if completed.returncode != 0:
        raise RecoveryError(f"age encryption failed: {completed.stderr.strip()}")
    if not destination.is_file() or destination.stat().st_size == 0:
        raise RecoveryError("age encryption produced no ciphertext")
    secure_private_path(destination, directory=False)


def _atomic_publish(source: Path, destination: Path, *, private: bool) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    if private:
        secure_private_directory(destination.parent)
    temporary = destination.with_name(f".{destination.name}.{os.getpid()}-{uuid.uuid4().hex}.partial")
    temporary.unlink(missing_ok=True)
    try:
        shutil.copy2(source, temporary)
        if private:
            secure_private_path(temporary, directory=False)
        os.replace(temporary, destination)
        if private:
            secure_private_path(destination, directory=False)
    finally:
        temporary.unlink(missing_ok=True)


def _write_sidecar(path: Path, value: dict[str, Any], *, private: bool) -> None:
    temporary = path.with_name(f".{path.name}.{os.getpid()}-{uuid.uuid4().hex}.partial")
    temporary.unlink(missing_ok=True)
    if private:
        create_private_file(temporary)
    try:
        temporary.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        if private:
            secure_private_path(temporary, directory=False)
        os.replace(temporary, path)
        if private:
            secure_private_path(path, directory=False)
    finally:
        temporary.unlink(missing_ok=True)


def _apply_retention(destination: Destination) -> list[str]:
    candidates = sorted(
        (
            path
            for path in destination.path.glob("hermes-recovery-*.tar.gz.age")
            if ARCHIVE_RE.fullmatch(path.name)
        ),
        key=lambda path: (path.stat().st_mtime_ns, path.name),
        reverse=True,
    )
    removed: list[str] = []
    for archive in candidates[destination.retention :]:
        # The exact file was discovered inside the explicit destination and
        # matched the recovery archive grammar; never follow a link.
        if is_reparse_point(archive):
            raise RecoveryError(f"Refusing to prune a reparse-point archive: {archive}")
        sidecar = archive.with_suffix(archive.suffix + ".json")
        archive.unlink()
        sidecar.unlink(missing_ok=True)
        removed.append(archive.name)
    return removed


def create_backup(plan: RecoveryPlan, *, full: bool = False) -> dict[str, Any]:
    started = _utc_now()
    started_at = _iso_utc(started)
    stamp = started.strftime("%Y%m%dT%H%M%SZ")
    run_id = uuid.uuid4().hex
    suffix = "-full" if full else ""
    archive_name = f"hermes-recovery-{stamp}-{run_id[:8]}{suffix}.tar.gz.age"
    secure_private_directory(plan.staging_root)
    stage = plan.staging_root / f"run-{run_id}"
    secure_private_directory(stage)
    payload = stage / "payload"
    payload.mkdir()
    plaintext_tar = stage / "payload.tar.gz"
    ciphertext = stage / archive_name
    selected_sources = [source for source in plan.sources if full or not source.full_only]
    source_records: list[dict[str, Any]] = []
    published: list[dict[str, Any]] = []
    error: BaseException | None = None
    try:
        with _backup_operation_lock(plan.hermes_home, timeout_seconds=5.0):
            with _paused_containers(
                [source.container for source in selected_sources if source.container]
            ):
                for source in selected_sources:
                    if not source.path.exists() and source.full_only:
                        continue
                    target = payload / source.name
                    if source.kind == "tree":
                        detail = _copy_tree(source.path, target)
                    elif source.kind == "desktop":
                        detail = _copy_desktop_state(source.path, target)
                    elif source.kind == "git-snapshot":
                        detail = _snapshot_repository(source.path, target)
                    else:  # pragma: no cover - load_plan rejects this
                        raise RecoveryError(f"Unsupported source kind: {source.kind}")
                    source_records.append(
                        {
                            "name": source.name,
                            "kind": source.kind,
                            "container_paused": source.container,
                            **detail,
                        }
                    )

            completed_at = _iso_utc()
            manifest = _manifest_for_payload(
                payload,
                run_id=run_id,
                started_at=started_at,
                completed_at=completed_at,
                full=full,
                source_records=source_records,
            )
            (stage / "manifest.json").write_text(
                json.dumps(manifest, indent=2, sort_keys=True) + "\n",
                encoding="utf-8",
            )
            _make_tar(stage, plaintext_tar)
            _encrypt(plan.age_executable, plan.recipient, plaintext_tar, ciphertext)
            ciphertext_sha256 = _sha256(ciphertext)
            sidecar = {
                "format": "hermes-encrypted-recovery-ciphertext",
                "version": 1,
                "archive": archive_name,
                "created_at": completed_at,
                "sha256": ciphertext_sha256,
                "bytes": ciphertext.stat().st_size,
                "full": full,
            }
            destination_errors: list[str] = []
            for destination in plan.destinations:
                try:
                    target = destination.path / archive_name
                    _atomic_publish(ciphertext, target, private=destination.private)
                    sidecar_path = target.with_suffix(target.suffix + ".json")
                    _write_sidecar(sidecar_path, sidecar, private=destination.private)
                    if _sha256(target) != ciphertext_sha256:
                        raise RecoveryError(f"Published ciphertext hash mismatch: {target}")
                    removed = _apply_retention(destination)
                    published.append(
                        {
                            "path": str(target),
                            "sha256": ciphertext_sha256,
                            "bytes": target.stat().st_size,
                            "retention_removed": removed,
                        }
                    )
                except (OSError, RecoveryError, PrivatePathError) as exc:
                    destination_errors.append(f"{destination.path}: {exc}")
                    if destination.required:
                        break
            if destination_errors:
                raise RecoveryError("Destination publication failed: " + "; ".join(destination_errors))
            result = {
                "status": "success",
                "run_id": run_id,
                "started_at": started_at,
                "completed_at": completed_at,
                "archive": archive_name,
                "full": full,
                "manifest": {
                    "file_count": manifest["file_count"],
                    "total_bytes": manifest["total_bytes"],
                },
                "sources": source_records,
                "destinations": published,
            }
            _write_json_private(plan.status_path, result)
            return result
    except BaseException as exc:
        error = exc
        try:
            _write_json_private(
                plan.status_path,
                {
                    "status": "failed",
                    "run_id": run_id,
                    "started_at": started_at,
                    "completed_at": _iso_utc(),
                    "error_type": type(exc).__name__,
                    "error": str(exc),
                },
            )
        except Exception:
            LOGGER.exception("Could not write recovery failure status")
        raise
    finally:
        # Cleanup is constrained to the generated child of the validated
        # staging root.  Never let a failed cleanup hide the primary failure.
        try:
            resolved_stage = stage.resolve(strict=False)
            resolved_root = plan.staging_root.resolve()
            if resolved_root not in resolved_stage.parents or not stage.name.startswith("run-"):
                raise RecoveryError(f"Refusing unsafe staging cleanup: {stage}")
            shutil.rmtree(stage, ignore_errors=False)
        except FileNotFoundError:
            pass
        except Exception:
            if error is None:
                raise
            LOGGER.exception("Could not remove private recovery staging tree")


def _safe_extract(archive_path: Path, destination: Path) -> None:
    with tarfile.open(archive_path, "r:gz") as archive:
        members = archive.getmembers()
        for member in members:
            pure = PurePosixPath(member.name)
            if pure.is_absolute() or ".." in pure.parts or not pure.parts:
                raise RecoveryError(f"Unsafe archive member path: {member.name}")
            if not (member.isdir() or member.isfile()):
                raise RecoveryError(f"Unsupported archive member type: {member.name}")
            target = destination.joinpath(*pure.parts)
            resolved = target.resolve(strict=False)
            root = destination.resolve()
            if resolved != root and root not in resolved.parents:
                raise RecoveryError(f"Archive member escaped restore root: {member.name}")
            if member.isdir():
                target.mkdir(parents=True, exist_ok=True)
                continue
            target.parent.mkdir(parents=True, exist_ok=True)
            source = archive.extractfile(member)
            if source is None:
                raise RecoveryError(f"Could not read archive member: {member.name}")
            with source, target.open("xb") as output:
                shutil.copyfileobj(source, output)


def _verify_restored_payload(destination: Path) -> dict[str, Any]:
    manifest_path = destination / "manifest.json"
    payload = destination / "payload"
    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise RecoveryError(f"Restored manifest is unreadable: {exc}") from exc
    if manifest.get("format") != "hermes-encrypted-recovery" or manifest.get("version") != 1:
        raise RecoveryError("Restored archive has an unsupported manifest")
    expected = {item["path"]: item for item in manifest.get("files", [])}
    actual = {
        path.relative_to(payload).as_posix(): path
        for path in payload.rglob("*")
        if path.is_file()
    }
    if set(expected) != set(actual):
        missing = sorted(set(expected) - set(actual))[:10]
        extra = sorted(set(actual) - set(expected))[:10]
        raise RecoveryError(f"Restored file inventory mismatch missing={missing} extra={extra}")
    sqlite_verified = 0
    for relative, record in expected.items():
        path = actual[relative]
        if path.stat().st_size != int(record["bytes"]) or _sha256(path) != record["sha256"]:
            raise RecoveryError(f"Restored file hash mismatch: {relative}")
        if "sqlite_quick_check" in record:
            _sqlite_quick_check(path)
            sqlite_verified += 1
    if len(expected) != int(manifest.get("file_count", -1)):
        raise RecoveryError("Manifest file count is internally inconsistent")
    return {
        "status": "verified",
        "run_id": manifest.get("run_id"),
        "file_count": len(expected),
        "total_bytes": sum(path.stat().st_size for path in actual.values()),
        "sqlite_verified": sqlite_verified,
        "verified_at": _iso_utc(),
    }


def restore_archive(
    plan: RecoveryPlan,
    *,
    archive_path: Path,
    identity_path: Path,
    destination: Path,
) -> dict[str, Any]:
    if not archive_path.is_file() or not ARCHIVE_RE.fullmatch(archive_path.name):
        raise RecoveryError(f"Not a Hermes encrypted recovery archive: {archive_path}")
    if not identity_path.is_file():
        raise RecoveryError(f"Recovery identity is missing: {identity_path}")
    # A child may inherit the already-private current-user/SYSTEM DACL from
    # the protected key directory.  Read back the effective principals; do
    # not require every child to carry a redundant protected DACL of its own.
    verify_private_path(identity_path, directory=False, require_protected=False)
    if destination.exists() and any(destination.iterdir()):
        raise RecoveryError(f"Restore destination must be absent or empty: {destination}")
    secure_private_directory(destination)
    decrypted = destination / f".decrypted-{uuid.uuid4().hex}.tar.gz"
    completed = subprocess.run(
        [
            str(plan.age_executable),
            "--decrypt",
            "--identity",
            str(identity_path),
            "--output",
            str(decrypted),
            str(archive_path),
        ],
        check=False,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    if completed.returncode != 0:
        decrypted.unlink(missing_ok=True)
        raise RecoveryError(f"age decryption failed: {completed.stderr.strip()}")
    secure_private_path(decrypted, directory=False)
    try:
        _safe_extract(decrypted, destination)
    finally:
        decrypted.unlink(missing_ok=True)
    result = _verify_restored_payload(destination)
    _write_json_private(destination / "restore-report.json", result)
    secured = secure_private_path(destination, directory=True, recursive=True)
    verified = verify_private_tree(destination)
    if secured != verified:
        raise RecoveryError("Private ACL read-back count changed during restore")
    return {**result, "private_objects_verified": verified, "destination": str(destination)}


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--plan", required=True, type=Path, help="Path to backup-plan.json")
    subparsers = parser.add_subparsers(dest="command", required=True)
    backup = subparsers.add_parser("backup", help="Create and publish an encrypted backup")
    backup.add_argument("--full", action="store_true", help="Include full-only private archives")
    restore = subparsers.add_parser("restore", help="Decrypt, restore, and verify into an empty path")
    restore.add_argument("--archive", required=True, type=Path)
    restore.add_argument("--identity", required=True, type=Path)
    restore.add_argument("--destination", required=True, type=Path)
    subparsers.add_parser("status", help="Read the last local run status")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    args = _build_parser().parse_args(argv)
    try:
        plan = load_plan(args.plan)
        if args.command == "backup":
            result = create_backup(plan, full=args.full)
        elif args.command == "restore":
            result = restore_archive(
                plan,
                archive_path=args.archive.resolve(),
                identity_path=_lexical_absolute(args.identity),
                destination=args.destination.resolve(),
            )
        elif args.command == "status":
            result = json.loads(plan.status_path.read_text(encoding="utf-8"))
        else:  # pragma: no cover
            raise RecoveryError(f"Unknown command: {args.command}")
    except (RecoveryError, BackupInProgressError, PrivatePathError, OSError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
