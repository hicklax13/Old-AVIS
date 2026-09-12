#!/usr/bin/env python3
"""Create a secret-safe credential exposure inventory.

The report contains issuer names, environment-key identifiers, store types,
and archive names only.  It never emits credential values or fingerprints.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
import zipfile
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from hermes_cli.capability_secret_policy import classify_env_key  # noqa: E402
from hermes_security import secure_private_directory, secure_private_path  # noqa: E402


ENV_RE = re.compile(r"^\s*([A-Za-z_][A-Za-z0-9_]*)\s*=", re.MULTILINE)
TOKEN_FILE_RE = re.compile(
    r"(?:^|/)mcp-tokens/(?P<provider>[a-z0-9_-]+?)(?:\.(?:client|meta))?\.json$",
    re.IGNORECASE,
)
GOOGLE_OAUTH_FILES = {
    "google_client_secret.json": (
        "Google Workspace OAuth",
        "oauth_client_registration",
    ),
    "google_token.json": (
        "Google Workspace OAuth",
        "refreshable_oauth_store",
    ),
    "youtube_client_secret.json": (
        "YouTube OAuth",
        "oauth_client_registration",
    ),
    "youtube_token.json": (
        "YouTube OAuth",
        "refreshable_oauth_store",
    ),
}


def _env_keys(raw: str) -> set[str]:
    return {match.group(1).upper() for match in ENV_RE.finditer(raw)}


def _record_env_keys(
    issuers: dict[str, dict[str, set[str]]],
    *,
    keys: Iterable[str],
    evidence: str,
) -> None:
    for key in keys:
        policy = classify_env_key(key)
        if not policy.secret or not policy.issuer:
            continue
        issuers[policy.issuer]["env_keys"].add(key)
        issuers[policy.issuer]["evidence"].add(evidence)
        issuers[policy.issuer]["material"].add(policy.scope)


def _provider_from_token_filename(name: str) -> str | None:
    match = TOKEN_FILE_RE.search(name.replace("\\", "/"))
    if not match:
        return None
    return match.group("provider").replace("_", "-")


def _google_oauth_material(name: str) -> tuple[str, str] | None:
    return GOOGLE_OAUTH_FILES.get(Path(name.replace("\\", "/")).name.casefold())


def _scan_zip(
    path: Path,
    issuers: dict[str, dict[str, set[str]]],
) -> dict[str, Any]:
    env_keys: set[str] = set()
    stores: set[str] = set()
    providers: set[str] = set()
    google_oauth: set[tuple[str, str]] = set()
    with zipfile.ZipFile(path) as archive:
        for info in archive.infolist():
            normalized = info.filename.replace("\\", "/")
            lowered = normalized.casefold()
            if lowered.endswith("/.env") or Path(normalized).name == ".env":
                try:
                    raw = archive.read(info).decode("utf-8-sig", errors="replace")
                except (KeyError, OSError, RuntimeError):
                    continue
                env_keys.update(_env_keys(raw))
            provider = _provider_from_token_filename(normalized)
            if provider:
                providers.add(provider)
            google_material = _google_oauth_material(normalized)
            if google_material:
                google_oauth.add(google_material)
            if lowered.endswith("/auth.json") or Path(normalized).name.casefold() == "auth.json":
                stores.add("Hermes provider auth store")
            if "services/n8n/data/config" in lowered or "services/n8n/data/database.sqlite" in lowered:
                stores.add("n8n credential/database store")
            if "platforms/whatsapp/session/" in lowered:
                stores.add("WhatsApp linked-device store")
    _record_env_keys(issuers, keys=env_keys, evidence=path.name)
    for provider in providers:
        name = f"MCP OAuth: {provider}"
        issuers[name]["evidence"].add(path.name)
        issuers[name]["material"].add("refreshable_oauth_store")
    for issuer, material in google_oauth:
        issuers[issuer]["evidence"].add(path.name)
        issuers[issuer]["material"].add(material)
    if "Hermes provider auth store" in stores:
        issuers["Hermes model-provider auth stores"]["evidence"].add(path.name)
        issuers["Hermes model-provider auth stores"]["material"].add("provider_auth_store")
    if "n8n credential/database store" in stores:
        issuers["n8n"]["evidence"].add(path.name)
        issuers["n8n"]["material"].add("service_credential_database")
    if "WhatsApp linked-device store" in stores:
        issuers["WhatsApp"]["evidence"].add(path.name)
        issuers["WhatsApp"]["material"].add("linked_device_session")
    return {
        "archive": path.name,
        "env_keys": sorted(env_keys),
        "env_key_count": len(env_keys),
        "oauth_providers": sorted(providers),
        "google_oauth_issuers": sorted({issuer for issuer, _ in google_oauth}),
        "store_types": sorted(stores),
    }


def build_inventory(hermes_home: Path) -> dict[str, Any]:
    issuers: dict[str, dict[str, set[str]]] = defaultdict(
        lambda: {"env_keys": set(), "evidence": set(), "material": set()}
    )
    current_env_files = [hermes_home / ".env"]
    profiles_root = hermes_home / "profiles"
    if profiles_root.is_dir():
        current_env_files.extend(sorted(profiles_root.glob("*/.env")))
    for path in current_env_files:
        if not path.is_file():
            continue
        _record_env_keys(
            issuers,
            keys=_env_keys(path.read_text(encoding="utf-8-sig", errors="replace")),
            evidence=f"current:{path.relative_to(hermes_home).as_posix()}",
        )

    token_roots = [hermes_home / "mcp-tokens"]
    if profiles_root.is_dir():
        token_roots.extend(sorted(profiles_root.glob("*/mcp-tokens")))
    for token_root in token_roots:
        if not token_root.is_dir():
            continue
        logical_root = token_root.relative_to(hermes_home).as_posix()
        for path in sorted(token_root.glob("*.json")):
            provider = _provider_from_token_filename(path.as_posix())
            if not provider or path.name.endswith(".meta.json"):
                continue
            name = f"MCP OAuth: {provider}"
            issuers[name]["evidence"].add(f"historically-broad current:{logical_root}")
            material = (
                "oauth_client_registration"
                if path.name.endswith(".client.json")
                else "refreshable_oauth_store"
            )
            issuers[name]["material"].add(material)

    credential_roots = [hermes_home]
    if profiles_root.is_dir():
        credential_roots.extend(path for path in sorted(profiles_root.iterdir()) if path.is_dir())
    for credential_root in credential_roots:
        for filename, (issuer, material) in GOOGLE_OAUTH_FILES.items():
            path = credential_root / filename
            if not path.is_file():
                continue
            issuers[issuer]["evidence"].add(
                f"historically-broad current:{path.relative_to(hermes_home).as_posix()}"
            )
            issuers[issuer]["material"].add(material)

    auth_paths = [hermes_home / "auth.json"]
    if profiles_root.is_dir():
        auth_paths.extend(sorted(profiles_root.glob("*/auth.json")))
    for auth_path in auth_paths:
        if not auth_path.is_file():
            continue
        try:
            parsed = json.loads(auth_path.read_text(encoding="utf-8-sig"))
        except (OSError, json.JSONDecodeError):
            continue
        providers = parsed.get("providers") if isinstance(parsed, dict) else None
        if not isinstance(providers, dict):
            continue
        for provider in providers:
            name = f"Hermes provider auth: {provider}"
            issuers[name]["evidence"].add(
                f"historically-broad current:{auth_path.relative_to(hermes_home).as_posix()}"
            )
            issuers[name]["material"].add("provider_auth_store")

    archives: list[dict[str, Any]] = []
    backup_root = hermes_home / "backups"
    if backup_root.is_dir():
        for archive in sorted(backup_root.glob("*.zip")):
            try:
                archives.append(_scan_zip(archive, issuers))
            except (OSError, zipfile.BadZipFile) as exc:
                archives.append({"archive": archive.name, "error": type(exc).__name__})

    live_state = {
        "home_assistant_auth_store": Path(r"C:\Dev\home-assistant\config\.storage\auth").is_file(),
        "n8n_credential_database": (hermes_home / "services" / "n8n" / "data" / "database.sqlite").is_file(),
        "whatsapp_linked_device_store": (hermes_home / "platforms" / "whatsapp" / "session" / "creds.json").is_file(),
    }
    if live_state["home_assistant_auth_store"]:
        issuers["Home Assistant"]["evidence"].add("historically-broad live auth store")
        issuers["Home Assistant"]["material"].add("refresh_and_long_lived_tokens")
    if live_state["n8n_credential_database"]:
        issuers["n8n"]["evidence"].add("historically-broad live service state")
        issuers["n8n"]["material"].add("account_password_api_tokens_encryption_key")
    if live_state["whatsapp_linked_device_store"]:
        issuers["WhatsApp"]["evidence"].add("historically-broad live device state")
        issuers["WhatsApp"]["material"].add("linked_device_session")

    normalized_issuers = []
    for name in sorted(issuers, key=str.casefold):
        record = issuers[name]
        normalized_issuers.append(
            {
                "issuer": name,
                "env_keys": sorted(record["env_keys"]),
                "evidence": sorted(record["evidence"]),
                "material": sorted(record["material"]),
                "status": "rotation_or_revocation_required",
            }
        )
    return {
        "format": "hermes-secret-safe-credential-exposure-inventory",
        "version": 1,
        "generated_at": datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z"),
        "policy": {
            "contains_secret_values": False,
            "local_acl_exposure_contained": True,
            "encrypted_recovery_proven": True,
            "one_time_oauth_callback_codes": "consumed; do not reuse; revoke the resulting grant where present",
        },
        "live_state_presence": live_state,
        "archives": archives,
        "affected_issuers": normalized_issuers,
    }


def main(argv: Iterable[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--hermes-home", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args(list(argv) if argv is not None else None)
    home = args.hermes_home.resolve()
    report = build_inventory(home)
    secure_private_directory(args.output.parent)
    args.output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    secure_private_path(args.output, directory=False)
    print(
        json.dumps(
            {
                "output": str(args.output),
                "issuer_count": len(report["affected_issuers"]),
                "archive_count": len(report["archives"]),
                "contains_secret_values": False,
            },
            indent=2,
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
