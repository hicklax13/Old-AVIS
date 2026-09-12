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
import hashlib
import os
import re
import shutil
import sys
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable

import yaml


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from hermes_security import (
    create_private_temp_file,
    is_reparse_point,
    secure_private_directory,
    secure_private_path,
)
from hermes_cli.capability_secret_policy import classify_env_key


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
    replaced_skills: dict[str, list[str]] = field(default_factory=dict)
    removed_service_local: dict[str, list[str]] = field(default_factory=dict)
    unmanaged_env_keys: list[str] = field(default_factory=list)
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
    mcp_owners: dict[str, str] = {}
    mcp_conflicts: list[str] = []
    platform_toolsets: dict[str, list[str]] = {}
    plugin_enabled: list[str] = []
    plugin_seen: set[str] = set()

    for profile in ordered:
        cfg = configs[profile.name]
        servers = cfg.get("mcp_servers")
        if isinstance(servers, dict):
            for name, entry in servers.items():
                if not isinstance(entry, dict):
                    continue
                enabled_entry = copy.deepcopy(entry)
                enabled_entry.pop("disabled", None)
                # Connor's baseline is enabled everywhere. The sole explicit
                # exception is a classified inactive capability: it must carry
                # both ``enabled: false`` and a human-readable blocked_reason.
                # That preserves no-paid-services / officially-unsupported /
                # absent-local states without allowing a stray false flag in
                # one profile to silently disable a working capability.
                blocked_reason = enabled_entry.get("blocked_reason")
                explicitly_blocked = (
                    enabled_entry.get("enabled") is False
                    and isinstance(blocked_reason, str)
                    and bool(blocked_reason.strip())
                )
                enabled_entry["enabled"] = not explicitly_blocked
                normalized_name = str(name)
                if normalized_name in mcp_servers:
                    if mcp_servers[normalized_name] != enabled_entry:
                        mcp_conflicts.append(
                            f"{normalized_name} ({mcp_owners[normalized_name]} != {profile.name})"
                        )
                    continue
                mcp_servers[normalized_name] = enabled_entry
                mcp_owners[normalized_name] = profile.name

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

    if mcp_conflicts:
        raise SyncError(
            "MCP definition conflicts require an explicit canonical choice: "
            + ", ".join(sorted(set(mcp_conflicts)))
        )

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


def _collect_env_union(
    profiles: list[ProfileHome],
    *,
    resolve_conflicts_from_default: bool = False,
) -> tuple[dict[str, str], dict[str, list[str]], list[str]]:
    """Return canonical shared values and service-local migration removals.

    ``default`` is the only credential authority. A shared key first appearing
    in another profile is refused instead of silently promoted. Unknown keys
    are refused regardless of their value so a suffix heuristic can never
    decide credential scope.
    """
    parsed = {profile.name: _parse_env_file(profile.path / ".env") for profile in profiles}
    default_values = parsed["default"]
    ambiguous: list[str] = []
    unmanaged: set[str] = set()
    service_local_removals: dict[str, list[str]] = {}
    for profile in profiles:
        for key in parsed[profile.name]:
            policy = classify_env_key(key)
            if policy.ambiguous:
                ambiguous.append(f"{key} ({profile.name}, {policy.scope})")
            elif not policy.shared:
                unmanaged.add(key)
                if policy.scope == "service_local" and profile.name != "default":
                    service_local_removals.setdefault(profile.name, []).append(key)
    if ambiguous:
        raise SyncError(
            "Ambiguous environment keys require explicit classification before sync: "
            + ", ".join(sorted(set(ambiguous)))
        )

    values = {
        key: value
        for key, value in default_values.items()
        if classify_env_key(key).shared
    }
    noncanonical: list[str] = []
    conflicts: list[str] = []
    for profile in profiles:
        for key, value in parsed[profile.name].items():
            if not classify_env_key(key).shared:
                continue
            if key not in default_values:
                noncanonical.append(f"{key} ({profile.name})")
            elif value != default_values[key]:
                conflicts.append(f"{key} (default != {profile.name})")
    if noncanonical:
        raise SyncError(
            "Shared account keys must first be installed in canonical default: "
            + ", ".join(sorted(set(noncanonical)))
        )
    if conflicts and not resolve_conflicts_from_default:
        raise SyncError(
            "Static account-key conflicts require an explicit owner choice: "
            + ", ".join(sorted(set(conflicts)))
        )
    return (
        values,
        {name: sorted(keys) for name, keys in service_local_removals.items()},
        sorted(unmanaged),
    )


def _skill_tree_digest(root: Path) -> str:
    digest = hashlib.sha256()
    for dirpath, dirnames, filenames in os.walk(root, topdown=True, followlinks=False):
        parent = Path(dirpath)
        dirnames[:] = sorted(
            name
            for name in dirnames
            if name not in _RUNTIME_SKILL_DIRS and not is_reparse_point(parent / name)
        )
        for name in sorted(filenames):
            path = parent / name
            if is_reparse_point(path) or name in _ignore_private_skill_files(str(parent), [name]):
                continue
            relative = path.relative_to(root).as_posix().encode("utf-8")
            digest.update(len(relative).to_bytes(4, "big"))
            digest.update(relative)
            with path.open("rb") as handle:
                for chunk in iter(lambda: handle.read(1024 * 1024), b""):
                    digest.update(chunk)
    return digest.hexdigest()


def _skill_sources(
    profiles: list[ProfileHome],
    *,
    resolve_conflicts_from_default: bool = False,
) -> tuple[dict[Path, Path], dict[str, list[Path]]]:
    """Map skill directories to sources and explicit default-led replacements."""
    sources: dict[Path, Path] = {}
    digests: dict[Path, str] = {}
    owners: dict[Path, str] = {}
    conflicts: list[str] = []
    replacements: dict[str, list[Path]] = {}
    ordered = sorted(profiles, key=lambda p: (p.name != "default", p.name))
    for profile in ordered:
        root = profile.path / "skills"
        if not root.is_dir():
            continue
        for manifest in sorted(root.rglob("SKILL.md")):
            rel = manifest.parent.relative_to(root)
            source = manifest.parent
            source_digest = _skill_tree_digest(source)
            if rel in sources:
                if digests[rel] != source_digest:
                    if resolve_conflicts_from_default and owners[rel] == "default":
                        replacements.setdefault(profile.name, []).append(rel)
                    else:
                        conflicts.append(f"{rel.as_posix()} ({owners[rel]} != {profile.name})")
                continue
            sources[rel] = source
            digests[rel] = source_digest
            owners[rel] = profile.name
    if conflicts:
        raise SyncError(
            "Skill definition conflicts require an explicit canonical choice: "
            + ", ".join(sorted(set(conflicts)))
        )
    return sources, {name: sorted(paths) for name, paths in replacements.items()}


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


def _render_env(
    original: str,
    current: dict[str, str],
    union: dict[str, str],
    *,
    remove_keys: set[str] | frozenset[str] = frozenset(),
    replace_values: dict[str, str] | None = None,
) -> str:
    replace_values = replace_values or {}
    if replace_values:
        from hermes_cli.config import _quote_env_value

    assignment = re.compile(r"^\s*([A-Za-z_][A-Za-z0-9_]*)\s*=")
    retained_lines: list[str] = []
    for line in original.splitlines():
        match = assignment.match(line)
        if match and match.group(1) in remove_keys:
            continue
        if match and match.group(1) in replace_values:
            key = match.group(1)
            retained_lines.append(f"{key}={_quote_env_value(replace_values[key])}")
            continue
        retained_lines.append(line)
    rendered = "\n".join(retained_lines)
    if original.endswith(("\n", "\r")):
        rendered += "\n"

    effective_current = {key: value for key, value in current.items() if key not in remove_keys}
    missing = [key for key in sorted(union) if key not in effective_current]
    if not missing:
        return rendered
    from hermes_cli.config import _quote_env_value

    rendered = rendered.rstrip()
    if rendered:
        rendered += "\n\n"
    rendered += "# Shared across profiles by scripts/sync_profile_capabilities.py\n"
    for key in missing:
        rendered += f"{key}={_quote_env_value(union[key])}\n"
    return rendered


def _atomic_write(path: Path, content: bytes, mode: int | None) -> None:
    del mode  # Capability/profile files are always private, regardless of legacy mode.
    secure_private_directory(path.parent)
    tmp_path = create_private_temp_file(
        path.parent,
        prefix=f".{path.name}.",
        suffix=".tmp",
    )
    try:
        with open(tmp_path, "wb") as handle:
            handle.write(content)
            handle.flush()
            os.fsync(handle.fileno())
        if path.exists():
            secure_private_path(path, directory=False)
        os.replace(tmp_path, path)
        secure_private_path(path, directory=False)
    finally:
        tmp_path.unlink(missing_ok=True)


def _backup_file(path: Path, profile: str, backup_root: Path) -> None:
    if not path.exists():
        return
    target = backup_root / profile / path.name
    secure_private_directory(target.parent)
    shutil.copy2(path, target)
    secure_private_path(target, directory=False)


def _backup_skill_tree(path: Path, profile: str, relative: Path, backup_root: Path) -> None:
    target = backup_root / profile / "skills" / relative
    secure_private_directory(target.parent)
    shutil.copytree(path, target, symlinks=True)
    secure_private_path(target, directory=True, recursive=True)


def _private_skill_files(root: Path) -> Iterable[tuple[Path, Path]]:
    for dirpath, dirnames, filenames in os.walk(root, topdown=True, followlinks=False):
        parent = Path(dirpath)
        dirnames[:] = [
            name
            for name in dirnames
            if name not in _RUNTIME_SKILL_DIRS and not is_reparse_point(parent / name)
        ]
        for name in filenames:
            path = parent / name
            if is_reparse_point(path):
                continue
            if name in _ignore_private_skill_files(str(parent), [name]):
                yield path.relative_to(root), path


def _replace_skill_tree(source: Path, target: Path) -> Path:
    """Atomically replace public skill code while retaining local secret files.

    Return the private sibling holding the old tree. The caller keeps it until
    every profile verifies, then deletes it; on any later failure it can swap
    the original tree back without reconstructing it from individual files.
    """
    if not target.is_dir():
        raise SyncError(f"Skill replacement target is missing: {target}")
    secure_private_directory(target.parent)
    nonce = uuid.uuid4().hex
    staged = target.parent / f".{target.name}.sync-new-{nonce}"
    original = target.parent / f".{target.name}.sync-old-{nonce}"
    try:
        shutil.copytree(source, staged, ignore=_ignore_private_skill_files)
        for relative, private_file in _private_skill_files(target):
            destination = staged / relative
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(private_file, destination)
        secure_private_path(staged, directory=True, recursive=True)
        os.replace(target, original)
        try:
            os.replace(staged, target)
            secure_private_path(target, directory=True, recursive=True)
        except BaseException:
            if target.exists():
                shutil.rmtree(target)
            os.replace(original, target)
            raise
        return original
    finally:
        if staged.exists():
            shutil.rmtree(staged)


def synchronize(
    root: Path,
    *,
    apply: bool = False,
    resolve_env_conflicts_from_default: bool = False,
    resolve_skill_conflicts_from_default: bool = False,
) -> SyncReport:
    """Plan or apply all-profile capability reconciliation."""
    profiles = discover_profiles(root)
    configs = {p.name: _read_mapping(p.path / "config.yaml") for p in profiles}
    union = _collect_capability_config(profiles, configs)
    env_union, service_local_removals, unmanaged_env_keys = _collect_env_union(
        profiles,
        resolve_conflicts_from_default=resolve_env_conflicts_from_default,
    )
    skill_sources, replacement_skills = _skill_sources(
        profiles,
        resolve_conflicts_from_default=resolve_skill_conflicts_from_default,
    )

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
        remove_keys = set(service_local_removals.get(profile.name, []))
        if (
            any(current_env.get(key) != value for key, value in env_union.items())
            or remove_keys
        ):
            env_newline = _newline_for(env_raw)
            env_original = env_raw.decode("utf-8-sig")
            rendered_env = _render_env(
                env_original,
                current_env,
                env_union,
                remove_keys=remove_keys,
                replace_values={
                    key: value
                    for key, value in env_union.items()
                    if current_env.get(key) != value
                },
            ).replace("\n", env_newline).encode("utf-8")
        else:
            # Preserve an existing BOM and exact newline bytes when no keys are
            # missing. A no-op reconciliation must remain byte-for-byte a no-op.
            rendered_env = env_raw
        if rendered_env != env_raw:
            env_updates[profile.name] = (env_path, rendered_env)

        skills_root = profile.path / "skills"
        profile_missing: list[Path] = []
        for rel in sorted(skill_sources):
            target = skills_root / rel
            if (target / "SKILL.md").is_file():
                continue
            if target.exists():
                raise SyncError(
                    f"Refusing to merge a skill into a partial target: {profile.name}:{rel.as_posix()}"
                )
            profile_missing.append(rel)
        missing_skills[profile.name] = profile_missing

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
        replaced_skills={
            name: [path.as_posix() for path in paths]
            for name, paths in replacement_skills.items()
            if paths
        },
        removed_service_local=service_local_removals,
        unmanaged_env_keys=unmanaged_env_keys,
    )

    if not apply:
        return report

    if (
        not config_updates
        and not env_updates
        and not any(missing_skills.values())
        and not any(replacement_skills.values())
    ):
        return report

    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    backup_root = root.resolve() / "backups" / "profile-capability-sync" / timestamp
    secure_private_directory(backup_root)
    report.backup_dir = str(backup_root)

    profile_by_name = {p.name: p for p in profiles}
    all_file_updates = [*config_updates.values(), *env_updates.values()]
    originals = {
        path: path.read_bytes() if path.exists() else None for path, _content in all_file_updates
    }
    for name, (path, _content) in config_updates.items():
        _backup_file(path, name, backup_root)
    for name, (path, _content) in env_updates.items():
        _backup_file(path, name, backup_root)
    for name, rel_paths in replacement_skills.items():
        target_root = profile_by_name[name].path / "skills"
        for rel in rel_paths:
            _backup_skill_tree(target_root / rel, name, rel, backup_root)

    created_skills: list[Path] = []
    replaced_skill_originals: list[tuple[Path, Path]] = []
    try:
        for _name, (path, content) in config_updates.items():
            mode = path.stat().st_mode if path.exists() else None
            _atomic_write(path, content, mode)

        for _name, (path, content) in env_updates.items():
            mode = path.stat().st_mode if path.exists() else 0o600
            _atomic_write(path, content, mode)
            secure_private_path(path, directory=False)

        for name, rel_paths in missing_skills.items():
            target_root = profile_by_name[name].path / "skills"
            for rel in rel_paths:
                target = target_root / rel
                shutil.copytree(
                    skill_sources[rel],
                    target,
                    ignore=_ignore_private_skill_files,
                )
                secure_private_path(target, directory=True, recursive=True)
                created_skills.append(target)

        for name, rel_paths in replacement_skills.items():
            target_root = profile_by_name[name].path / "skills"
            for rel in rel_paths:
                target = target_root / rel
                original = _replace_skill_tree(skill_sources[rel], target)
                replaced_skill_originals.append((target, original))

        # Fresh read-back proves the materialized state, not only the write plan.
        for profile in profiles:
            cfg = _read_mapping(profile.path / "config.yaml")
            for key in ("mcp_servers", "platform_toolsets", "plugins"):
                if cfg.get(key) != union[key]:
                    raise SyncError(f"Post-write verification failed for {profile.name}:{key}")
            env = _parse_env_file(profile.path / ".env")
            if any(env.get(key) != value for key, value in env_union.items()):
                raise SyncError(f"Post-write environment verification failed for {profile.name}")
            forbidden = set(service_local_removals.get(profile.name, []))
            if forbidden.intersection(env):
                raise SyncError(
                    f"Post-write service-local migration failed for {profile.name}: "
                    + ", ".join(sorted(forbidden.intersection(env)))
                )
            for rel in skill_sources:
                if not (profile.path / "skills" / rel / "SKILL.md").is_file():
                    raise SyncError(f"Post-write skill verification failed for {profile.name}:{rel}")
                if _skill_tree_digest(profile.path / "skills" / rel) != _skill_tree_digest(
                    skill_sources[rel]
                ):
                    raise SyncError(
                        f"Post-write skill-content verification failed for "
                        f"{profile.name}:{rel.as_posix()}"
                    )
    except BaseException as exc:
        rollback_errors: list[str] = []
        allowed_skill_roots = {
            (profile.path / "skills").resolve(strict=False) for profile in profiles
        }
        for target, original in reversed(replaced_skill_originals):
            try:
                resolved_target = target.resolve(strict=False)
                if not any(root in resolved_target.parents for root in allowed_skill_roots):
                    raise SyncError(f"Unsafe skill replacement rollback target: {target}")
                if target.exists():
                    shutil.rmtree(target)
                os.replace(original, target)
                secure_private_path(target, directory=True, recursive=True)
            except Exception as rollback_exc:
                rollback_errors.append(f"{target}: {rollback_exc}")
        for target in reversed(created_skills):
            try:
                resolved_target = target.resolve(strict=False)
                if not any(root in resolved_target.parents for root in allowed_skill_roots):
                    raise SyncError(f"Unsafe skill rollback target: {target}")
                shutil.rmtree(target)
            except Exception as rollback_exc:
                rollback_errors.append(f"{target}: {rollback_exc}")
        for path, content in reversed(list(originals.items())):
            try:
                if content is None:
                    path.unlink(missing_ok=True)
                else:
                    _atomic_write(path, content, None)
            except Exception as rollback_exc:
                rollback_errors.append(f"{path}: {rollback_exc}")
        secure_private_path(backup_root, directory=True, recursive=True)
        message = f"Capability sync failed and was rolled back: {exc}"
        if rollback_errors:
            message += "; rollback errors: " + "; ".join(rollback_errors)
        raise SyncError(message) from exc

    for _target, original in replaced_skill_originals:
        if original.exists():
            shutil.rmtree(original)
    secure_private_path(backup_root, directory=True, recursive=True)

    return report


def _print_report(report: SyncReport, *, applied: bool) -> None:
    mode = "Applied" if applied else "Dry run"
    print(f"{mode}: {len(report.profiles)} profile(s)")
    print(f"  MCP server states synchronized everywhere: {len(report.mcp_servers)}")
    print(f"  Installed skill paths everywhere: {len(report.skill_paths)}")
    print(f"  Static account/env keys everywhere: {len(report.env_keys)}")
    print(f"  Known profile-local/service/local env keys unmanaged: {len(report.unmanaged_env_keys)}")
    print(
        f"  Service-local env keys {'removed' if applied else 'to remove'} from named profiles: "
        f"{sum(len(keys) for keys in report.removed_service_local.values())}"
    )
    print(f"  Config files {'changed' if applied else 'to change'}: {len(report.changed_configs)}")
    print(f"  Env files {'changed' if applied else 'to change'}: {len(report.changed_envs)}")
    print(
        f"  Skill copies {'made' if applied else 'to make'}: "
        f"{sum(len(paths) for paths in report.copied_skills.values())}"
    )
    print(
        f"  Default-authorized skill replacements {'made' if applied else 'to make'}: "
        f"{sum(len(paths) for paths in report.replaced_skills.values())}"
    )
    if report.backup_dir:
        print(f"  Recoverable backup: {report.backup_dir}")


def main(argv: Iterable[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--apply", action="store_true", help="write the planned reconciliation")
    parser.add_argument(
        "--resolve-env-conflicts-from-default",
        action="store_true",
        help=(
            "explicitly authorize canonical default shared env values to replace "
            "conflicting shared values in named profiles"
        ),
    )
    parser.add_argument(
        "--resolve-skill-conflicts-from-default",
        action="store_true",
        help=(
            "explicitly authorize the canonical default profile to replace "
            "conflicting public skill code while preserving profile-local secret files"
        ),
    )
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
        report = synchronize(
            root,
            apply=args.apply,
            resolve_env_conflicts_from_default=args.resolve_env_conflicts_from_default,
            resolve_skill_conflicts_from_default=args.resolve_skill_conflicts_from_default,
        )
    except SyncError as exc:
        print(f"Profile capability sync refused: {exc}", file=sys.stderr)
        return 2
    _print_report(report, applied=args.apply)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
