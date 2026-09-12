#!/usr/bin/env python3
"""Install a copied n8n API key without exposing it in logs or argv.

The script reads the replacement key from the Windows clipboard, verifies both
the current and replacement keys against the local n8n API, preserves a
private rollback copy of the old env file, atomically installs the replacement,
and clears the clipboard.  It never prints either credential.
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from hermes_security import (  # noqa: E402
    create_private_temp_file,
    secure_private_directory,
    secure_private_path,
    verify_private_path,
)


def _read_clipboard() -> str:
    if sys.platform != "win32":
        raise RuntimeError("Clipboard rotation is supported only on Windows")
    completed = subprocess.run(
        [
            "powershell.exe",
            "-NoProfile",
            "-NonInteractive",
            "-Command",
            "Get-Clipboard -Raw",
        ],
        check=True,
        capture_output=True,
        text=True,
        timeout=15,
    )
    return completed.stdout.strip()


def _clear_clipboard() -> None:
    if sys.platform != "win32":
        return
    subprocess.run(
        [
            "powershell.exe",
            "-NoProfile",
            "-NonInteractive",
            "-Command",
            "Set-Clipboard -Value $null",
        ],
        check=False,
        capture_output=True,
        text=True,
        timeout=15,
    )


def _parse_env(text: str) -> tuple[list[str], dict[str, str]]:
    lines = text.splitlines()
    values: dict[str, str] = {}
    for line in lines:
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        values[key.strip()] = value.strip()
    return lines, values


def _replace_env_value(lines: list[str], key: str, value: str) -> str:
    replacement = f"{key}={value}"
    found = False
    updated: list[str] = []
    for line in lines:
        if not line.lstrip().startswith("#") and "=" in line:
            current_key = line.split("=", 1)[0].strip()
            if current_key == key:
                updated.append(replacement)
                found = True
                continue
        updated.append(line)
    if not found:
        updated.append(replacement)
    return "\n".join(updated) + "\n"


def _api_status(base_url: str, api_key: str) -> int:
    query = urlencode({"limit": 1})
    request = Request(
        f"{base_url.rstrip('/')}/api/v1/workflows?{query}",
        headers={"X-N8N-API-KEY": api_key, "Accept": "application/json"},
    )
    try:
        with urlopen(request, timeout=15) as response:  # noqa: S310 - local URL
            return int(response.status)
    except HTTPError as exc:
        return int(exc.code)
    except URLError as exc:
        raise RuntimeError(f"n8n API is unreachable: {exc.reason}") from exc


def _private_atomic_write(path: Path, content: str) -> None:
    secure_private_directory(path.parent)
    if path.exists():
        secure_private_path(path, directory=False)
    temporary = create_private_temp_file(path.parent, prefix=f".{path.name}.")
    try:
        with temporary.open("w", encoding="utf-8", newline="\n") as handle:
            handle.write(content)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
        secure_private_path(path, directory=False)
    finally:
        temporary.unlink(missing_ok=True)


def install_from_clipboard(env_path: Path, pending_path: Path) -> dict[str, object]:
    if not env_path.is_file():
        raise RuntimeError(f"n8n env file does not exist: {env_path}")
    if pending_path.exists():
        raise RuntimeError(
            "A pending n8n rotation already exists; finish or roll it back first"
        )

    secure_private_path(env_path, directory=False)
    old_text = env_path.read_text(encoding="utf-8")
    lines, values = _parse_env(old_text)
    old_key = values.get("N8N_API_KEY", "")
    base_url = values.get("N8N_BASE_URL", "http://127.0.0.1:5678")
    if len(old_key) < 64:
        raise RuntimeError("Existing N8N_API_KEY is missing or malformed")

    try:
        new_key = _read_clipboard()
    finally:
        _clear_clipboard()
    if "\n" in new_key or "\r" in new_key or len(new_key) < 64:
        raise RuntimeError("Clipboard does not contain one valid-looking n8n API key")
    if new_key == old_key:
        raise RuntimeError("Clipboard contains the existing n8n API key, not a replacement")

    old_status = _api_status(base_url, old_key)
    new_status = _api_status(base_url, new_key)
    if old_status >= 400:
        raise RuntimeError(f"Existing n8n API key baseline failed with HTTP {old_status}")
    if new_status >= 400:
        raise RuntimeError(f"Replacement n8n API key failed with HTTP {new_status}")

    secure_private_directory(pending_path.parent)
    _private_atomic_write(pending_path, old_text)
    try:
        new_text = _replace_env_value(lines, "N8N_API_KEY", new_key)
        _private_atomic_write(env_path, new_text)
        _, readback = _parse_env(env_path.read_text(encoding="utf-8"))
        if readback.get("N8N_API_KEY") != new_key:
            raise RuntimeError("n8n env read-back did not contain the replacement key")
        verify_private_path(env_path, directory=False)
        verify_private_path(pending_path, directory=False)
    except BaseException:
        _private_atomic_write(env_path, old_text)
        pending_path.unlink(missing_ok=True)
        raise

    return {
        "installed": True,
        "old_key_baseline_status": old_status,
        "new_key_status": new_status,
        "env_private": True,
        "rollback_private": True,
        "clipboard_cleared": True,
        "pending_path": str(pending_path),
    }


def finalize_rotation(env_path: Path, pending_path: Path) -> dict[str, object]:
    """Prove the old key is revoked, prove the new key works, then clean up."""
    if not env_path.is_file():
        raise RuntimeError(f"n8n env file does not exist: {env_path}")
    if not pending_path.is_file():
        raise RuntimeError(f"Pending n8n rotation state does not exist: {pending_path}")

    secure_private_path(env_path, directory=False)
    secure_private_path(pending_path, directory=False)
    _, current = _parse_env(env_path.read_text(encoding="utf-8"))
    _, previous = _parse_env(pending_path.read_text(encoding="utf-8"))
    new_key = current.get("N8N_API_KEY", "")
    old_key = previous.get("N8N_API_KEY", "")
    base_url = current.get("N8N_BASE_URL", "http://127.0.0.1:5678")
    if len(new_key) < 64 or len(old_key) < 64:
        raise RuntimeError("Current or previous n8n API key is missing or malformed")
    if new_key == old_key:
        raise RuntimeError("Current and previous n8n API keys are identical")

    new_status = _api_status(base_url, new_key)
    old_status = _api_status(base_url, old_key)
    if new_status >= 400:
        raise RuntimeError(f"Replacement n8n API key failed with HTTP {new_status}")
    if old_status < 400:
        raise RuntimeError(
            f"Previous n8n API key is still authorized with HTTP {old_status}"
        )
    if old_status not in {401, 403}:
        raise RuntimeError(
            f"Previous n8n API key failed ambiguously with HTTP {old_status}"
        )

    pending_path.unlink()
    if pending_path.exists():
        raise RuntimeError("Could not remove pending n8n rotation state")
    return {
        "finalized": True,
        "new_key_status": new_status,
        "old_key_status": old_status,
        "old_key_revoked": True,
        "rollback_removed": True,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--env",
        type=Path,
        default=REPO_ROOT / ".hermes" / "mcp" / "n8n" / "env",
    )
    parser.add_argument(
        "--pending",
        type=Path,
        default=(
            REPO_ROOT
            / ".hermes"
            / "recovery"
            / "credential-rotation"
            / "n8n-env-before-api-key-rotation.pending"
        ),
    )
    parser.add_argument(
        "--finalize",
        action="store_true",
        help="verify old-key revocation and remove the private rollback copy",
    )
    args = parser.parse_args()
    try:
        if args.finalize:
            result = finalize_rotation(args.env, args.pending)
        else:
            result = install_from_clipboard(args.env, args.pending)
    except Exception as exc:
        print(json.dumps({"installed": False, "error": str(exc)}))
        return 1
    print(json.dumps(result, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
