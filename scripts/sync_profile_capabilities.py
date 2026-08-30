"""Reconcile installed capabilities across every local Hermes profile.

This is an operator command, not a runtime inheritance layer.  Profiles keep
their own persona, memories, sessions, model choices, and refreshable OAuth
stores.  The command synchronizes only capability declarations, installed
skill code, and non-conflicting static ``.env`` account keys.

Run without ``--apply`` for a dry run.  Applied changes are backed up below
``<HERMES_HOME>/backups/profile-capability-sync/`` before replacement.
"""

from __future__ import annotations

import argparse
import copy
import fnmatch
import os
import re
import shutil
import sys
import tempfile
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable

import yaml


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


_PROFILE_ID_RE = re.compile(r"^[a-z0-9][a-z0-9_-]{0,63}$")
_PRIVATE_SKILL_FILE_PATTERNS = (
    ".env",
    ".env.*",
    "auth.json",
    "credentials.json",
    "*client_secret*.json",
    "*oauth_pending*.json",
    "*token.json",
    "*_token.json",
    "*.key",
    "*.p12",
    "*.pem",
    "*.pfx",
)
_RUNTIME_SKILL_DIRS = frozenset(
    {".git", ".venv", "__pycache__", "node_modules", "venv"}
)


class SyncError(RuntimeError):
    """Raised before mutation when capability state cannot be merged safely."""


@dataclass(frozen=True)
class ProfileHome:
    name: str
    path: Path


@dataclass
class SyncReport:
    profiles: list[str]
    mcp_servers: list[str]
    skill_paths: list[str]
    env_keys: list[str]
    changed_configs: list[str] = field(default_factory=list)
    changed_envs: list[str] = field(default_factory=list)
    copied_skills: dict[str, list[str]] = field(default_factory=dict)
    backup_dir: str | None = None


def discover_profiles(root: Path) -> list[ProfileHome]:
    """Return the default profile followed by every valid named profile."""
    root = root.resolve()
    profiles = [ProfileHome("default", root)]
    profiles_root = root / "profiles"
    if profiles_root.is_dir():
        for entry in sorted(profiles_root.iterdir(), key=lambda p: p.name):
            if entry.is_dir() and _PROFILE_ID_RE.fullmatch(entry.name):
                profiles.append(ProfileHome(entry.name, entry.resolve()))
    return profiles


def _read_mapping(path: Path) -> dict[str, Any]:
    try:
        parsed = yaml.safe_load(path.read_text(encoding="utf-8-sig")) or {}
    except FileNotFoundError:
        return {}
    except Exception as exc:
        raise SyncError(f"Refusing to rewrite unreadable YAML {path}: {exc}") from exc
    if not isinstance(parsed, dict):
        raise SyncError(f"Refusing to rewrite {path}: top-level YAML is not a mapping")
    return parsed


def _deep_merge_missing(target: dict[str, Any], incoming: dict[str, Any]) -> None:
    """Merge only missing leaves from *incoming* into *target*."""
    for key, value in incoming.items():
        if key not in target:
            target[key] = copy.deepcopy(value)
        elif isinstance(target[key], dict) and isinstance(value, dict):
            _deep_merge_missing(target[key], value)


def _collect_capability_config(
    profiles: list[ProfileHome],
    configs: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    """Build one deterministic union; default wins definition conflicts."""
    ordered = sorted(profiles, key=lambda p: (p.name != "default", p.name))
    mcp_servers: dict[str, Any] = {}
    platform_toolsets: dict[str, list[str]] = {}
    plugin_enabled: list[str] = []
    plugin_seen: set[str] = set()

    for profile in ordered:
        cfg = configs[profile.name]
        servers = cfg.get("mcp_servers")
        if isinstance(servers, dict):
            for name, entry in servers.items():
                if name in mcp_servers or not isinstance(entry, dict):
                    continue
                enabled_entry = copy.deepcopy(entry)
                enabled_entry.pop("disabled", None)
                enabled_entry["enabled"] = True
                mcp_servers[str(name)] = enabled_entry

        platform_cfg = cfg.get("platform_toolsets")
        if isinstance(platform_cfg, dict):
            for platform, names in platform_cfg.items():
                if not isinstance(names, list):
                    continue
                bucket = platform_toolsets.setdefault(str(platform), [])
                for name in names:
                    normalized = str(name).strip()
                    if normalized and normalized not in bucket:
                        bucket.append(normalized)

        plugins = cfg.get("plugins")
        enabled = plugins.get("enabled") if isinstance(plugins, dict) else None
        if isinstance(enabled, list):
            for name in enabled:
                normalized = str(name).strip()
                if normalized and normalized not in plugin_seen:
                    plugin_seen.add(normalized)
                    plugin_enabled.append(normalized)

    # Validate after the union is settled and before any file can be changed.
    from hermes_cli.mcp_config import validate_mcp_server_entry

    validation_errors: list[str] = []
    for name, entry in mcp_servers.items():
        validation_errors.extend(validate_mcp_server_entry(name, entry))
    if validation_errors:
        raise SyncError("Unsafe MCP definition in capability union: " + "; ".join(validation_errors))

    return {
        "mcp_servers": mcp_servers,
        "platform_toolsets": platform_toolsets,
        "plugins": {"enabled": plugin_enabled, "disabled": []},
    }


def _parse_env_file(path: Path) -> dict[str, str]:
    if not path.exists():
        return {}
    from agent.secret_scope import load_env_file

    return load_env_file(path)


def _collect_env_union(profiles: list[ProfileHome]) -> dict[str, str]:
    values: dict[str, str] = {}
    owners: dict[str, str] = {}
    conflicts: list[str] = []
    for profile in profiles:
        for key, value in _parse_env_file(profile.path / ".env").items():
            if key in values and values[key] != value:
                conflicts.append(f"{key} ({owners[key]} != {profile.name})")
                continue
            values[key] = value
            owners.setdefault(key, profile.name)
    if conflicts:
        raise SyncError(
            "Static account-key conflicts require an explicit owner choice: "
            + ", ".join(sorted(set(conflicts)))
        )
    return values


def _skill_sources(profiles: list[ProfileHome]) -> dict[Path, Path]:
    """Map relative skill directory to source; default wins conflicts."""
    sources: dict[Path, Path] = {}
    ordered = sorted(profiles, key=lambda p: (p.name != "default", p.name))
    for profile in ordered:
        root = profile.path / "skills"
        if not root.is_dir():
            continue
        for manifest in sorted(root.rglob("SKILL.md")):
            rel = manifest.parent.relative_to(root)
            sources.setdefault(rel, manifest.parent)
    return sources


def _ignore_private_skill_files(_directory: str, names: list[str]) -> set[str]:
    ignored: set[str] = set()
    for name in names:
        if name in _RUNTIME_SKILL_DIRS:
            ignored.add(name)
            continue
        if any(fnmatch.fnmatch(name.lower(), pattern.lower()) for pattern in _PRIVATE_SKILL_FILE_PATTERNS):
            ignored.add(name)
    return ignored


def _newline_for(raw: bytes) -> str:
    return "\r\n" if b"\r\n" in raw else "\n"


def _replace_top_level_section(text: str, key: str, value: Any) -> str:
    """Replace one top-level YAML section without reformatting the rest."""
    lines = text.splitlines()
    start: int | None = None
    end = len(lines)
    for index, line in enumerate(lines):
        if line.startswith(f"{key}:"):
            start = index
            break
    if start is not None:
        for index in range(start + 1, len(lines)):
            line = lines[index]
            if line and not line[0].isspace() and not line.startswith("#"):
                end = index
                break

    replacement = yaml.safe_dump(
        {key: value},
        allow_unicode=True,
        default_flow_style=False,
        sort_keys=False,
    ).rstrip().splitlines()
    if start is None:
        while lines and not lines[-1].strip():
            lines.pop()
        if lines:
            lines.append("")
        lines.extend(replacement)
    else:
        lines[start:end] = replacement
    return "\n".join(lines).rstrip() + "\n"


def _render_config(original: str, union: dict[str, Any]) -> str:
    rendered = original
    for key in ("mcp_servers", "platform_toolsets", "plugins"):
        rendered = _replace_top_level_section(rendered, key, union[key])

    parsed = yaml.safe_load(rendered) or {}
    if not isinstance(parsed, dict):
        raise SyncError("Rendered config is not a YAML mapping")
    for key in ("mcp_servers", "platform_toolsets", "plugins"):
        if parsed.get(key) != union[key]:
            raise SyncError(f"Rendered config failed round-trip verification for {key}")
    return rendered


def _render_env(original: str, current: dict[str, str], union: dict[str, str]) -> str:
    missing = [key for key in sorted(union) if key not in current]
    if not missing:
        return original
    from hermes_cli.config import _quote_env_value

    rendered = original.rstrip()
    if rendered:
        rendered += "\n\n"
    rendered += "# Shared across profiles by scripts/sync_profile_capabilities.py\n"
    for key in missing:
        rendered += f"{key}={_quote_env_value(union[key])}\n"
    return rendered


def _atomic_write(path: Path, content: bytes, mode: int | None) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp_name = tempfile.mkstemp(prefix=f".{path.name}.", suffix=".tmp", dir=str(path.parent))
    tmp_path = Path(tmp_name)
    try:
        with os.fdopen(fd, "wb") as handle:
            handle.write(content)
            handle.flush()
            os.fsync(handle.fileno())
        if mode is not None:
            os.chmod(tmp_path, mode)
        os.replace(tmp_path, path)
    finally:
        tmp_path.unlink(missing_ok=True)


def _backup_file(path: Path, profile: str, backup_root: Path) -> None:
    if not path.exists():
        return
    target = backup_root / profile / path.name
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(path, target)


def synchronize(root: Path, *, apply: bool = False) -> SyncReport:
    """Plan or apply all-profile capability reconciliation."""
    profiles = discover_profiles(root)
    configs = {p.name: _read_mapping(p.path / "config.yaml") for p in profiles}
    union = _collect_capability_config(profiles, configs)
    env_union = _collect_env_union(profiles)
    skill_sources = _skill_sources(profiles)

    config_updates: dict[str, tuple[Path, bytes]] = {}
    env_updates: dict[str, tuple[Path, bytes]] = {}
    missing_skills: dict[str, list[Path]] = {}

    for profile in profiles:
        config_path = profile.path / "config.yaml"
        raw = config_path.read_bytes() if config_path.exists() else b""
        newline = _newline_for(raw)
        original = raw.decode("utf-8-sig")
        rendered = _render_config(original, union).replace("\n", newline).encode("utf-8")
        if rendered != raw:
            config_updates[profile.name] = (config_path, rendered)

        env_path = profile.path / ".env"
        env_raw = env_path.read_bytes() if env_path.exists() else b""
        current_env = _parse_env_file(env_path)
        if any(key not in current_env for key in env_union):
            env_newline = _newline_for(env_raw)
            env_original = env_raw.decode("utf-8-sig")
            rendered_env = _render_env(
                env_original,
                current_env,
                env_union,
            ).replace("\n", env_newline).encode("utf-8")
        else:
            # Preserve an existing BOM and exact newline bytes when no keys are
            # missing. A no-op reconciliation must remain byte-for-byte a no-op.
            rendered_env = env_raw
        if rendered_env != env_raw:
            env_updates[profile.name] = (env_path, rendered_env)

        skills_root = profile.path / "skills"
        missing_skills[profile.name] = [
            rel for rel in sorted(skill_sources) if not (skills_root / rel / "SKILL.md").is_file()
        ]

    report = SyncReport(
        profiles=[p.name for p in profiles],
        mcp_servers=sorted(union["mcp_servers"]),
        skill_paths=[str(path).replace("\\", "/") for path in sorted(skill_sources)],
        env_keys=sorted(env_union),
        changed_configs=sorted(config_updates),
        changed_envs=sorted(env_updates),
        copied_skills={
            name: [str(path).replace("\\", "/") for path in paths]
            for name, paths in missing_skills.items()
            if paths
        },
    )

    if not apply:
        return report

    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    backup_root = root.resolve() / "backups" / "profile-capability-sync" / timestamp
    report.backup_dir = str(backup_root)

    profile_by_name = {p.name: p for p in profiles}
    for name, (path, content) in config_updates.items():
        _backup_file(path, name, backup_root)
        mode = path.stat().st_mode if path.exists() else None
        _atomic_write(path, content, mode)

    for name, (path, content) in env_updates.items():
        _backup_file(path, name, backup_root)
        mode = path.stat().st_mode if path.exists() else 0o600
        _atomic_write(path, content, mode)
        try:
            from tools.mcp_oauth import _secure_windows_credential_acl

            _secure_windows_credential_acl(path, directory=False)
        except Exception:
            pass

    for name, rel_paths in missing_skills.items():
        target_root = profile_by_name[name].path / "skills"
        for rel in rel_paths:
            target = target_root / rel
            shutil.copytree(
                skill_sources[rel],
                target,
                dirs_exist_ok=True,
                ignore=_ignore_private_skill_files,
            )

    # Fresh read-back proves the materialized state, not only the write plan.
    for profile in profiles:
        cfg = _read_mapping(profile.path / "config.yaml")
        for key in ("mcp_servers", "platform_toolsets", "plugins"):
            if cfg.get(key) != union[key]:
                raise SyncError(f"Post-write verification failed for {profile.name}:{key}")
        env = _parse_env_file(profile.path / ".env")
        if any(env.get(key) != value for key, value in env_union.items()):
            raise SyncError(f"Post-write environment verification failed for {profile.name}")
        for rel in skill_sources:
            if not (profile.path / "skills" / rel / "SKILL.md").is_file():
                raise SyncError(f"Post-write skill verification failed for {profile.name}:{rel}")

    return report


def _print_report(report: SyncReport, *, applied: bool) -> None:
    mode = "Applied" if applied else "Dry run"
    print(f"{mode}: {len(report.profiles)} profile(s)")
    print(f"  MCP servers enabled everywhere: {len(report.mcp_servers)}")
    print(f"  Installed skill paths everywhere: {len(report.skill_paths)}")
    print(f"  Static account/env keys everywhere: {len(report.env_keys)}")
    print(f"  Config files {'changed' if applied else 'to change'}: {len(report.changed_configs)}")
    print(f"  Env files {'changed' if applied else 'to change'}: {len(report.changed_envs)}")
    print(
        f"  Skill copies {'made' if applied else 'to make'}: "
        f"{sum(len(paths) for paths in report.copied_skills.values())}"
    )
    if report.backup_dir:
        print(f"  Recoverable backup: {report.backup_dir}")


def main(argv: Iterable[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--apply", action="store_true", help="write the planned reconciliation")
    parser.add_argument(
        "--root",
        type=Path,
        help="default HERMES_HOME (defaults to the active installation's default profile)",
    )
    args = parser.parse_args(list(argv) if argv is not None else None)

    if args.root is None:
        from hermes_cli.profiles import get_profile_dir

        root = Path(get_profile_dir("default"))
    else:
        root = args.root

    try:
        report = synchronize(root, apply=args.apply)
    except SyncError as exc:
        print(f"Profile capability sync refused: {exc}", file=sys.stderr)
        return 2
    _print_report(report, applied=args.apply)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
