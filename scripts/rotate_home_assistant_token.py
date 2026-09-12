#!/usr/bin/env python3
"""Safely rotate the shared Home Assistant token from the Windows clipboard."""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import urlparse
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


def _validate_base_url(base_url: str) -> str:
    parsed = urlparse(base_url)
    if parsed.scheme not in {"http", "https"} or not parsed.hostname:
        raise RuntimeError("HASS_URL is not a valid HTTP(S) URL")
    return base_url.rstrip("/")


def _api_status(base_url: str, token: str) -> int:
    request = Request(
        f"{_validate_base_url(base_url)}/api/",
        headers={"Authorization": f"Bearer {token}", "Accept": "application/json"},
    )
    try:
        with urlopen(request, timeout=15) as response:  # noqa: S310 - configured HA URL
            return int(response.status)
    except HTTPError as exc:
        return int(exc.code)
    except URLError as exc:
        raise RuntimeError(f"Home Assistant API is unreachable: {exc.reason}") from exc


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
        raise RuntimeError(f"Hermes env file does not exist: {env_path}")
    if pending_path.exists():
        raise RuntimeError(
            "A pending Home Assistant rotation already exists; finish or roll it back first"
        )

    secure_private_path(env_path, directory=False)
    old_text = env_path.read_text(encoding="utf-8")
    lines, values = _parse_env(old_text)
    old_token = values.get("HASS_TOKEN", "")
    base_url = values.get("HASS_URL", "")
    _validate_base_url(base_url)
    if len(old_token) < 64:
        raise RuntimeError("Existing HASS_TOKEN is missing or malformed")

    try:
        new_token = _read_clipboard()
    finally:
        _clear_clipboard()
    if any(char.isspace() for char in new_token) or len(new_token) < 64:
        raise RuntimeError(
            "Clipboard does not contain one valid-looking Home Assistant token"
        )
    if new_token == old_token:
        raise RuntimeError(
            "Clipboard contains the existing Home Assistant token, not a replacement"
        )

    old_status = _api_status(base_url, old_token)
    new_status = _api_status(base_url, new_token)
    if old_status != 200:
        raise RuntimeError(
            f"Existing Home Assistant token baseline failed with HTTP {old_status}"
        )
    if new_status != 200:
        raise RuntimeError(
            f"Replacement Home Assistant token failed with HTTP {new_status}"
        )

    secure_private_directory(pending_path.parent)
    _private_atomic_write(pending_path, old_text)
    try:
        new_text = _replace_env_value(lines, "HASS_TOKEN", new_token)
        _private_atomic_write(env_path, new_text)
        _, readback = _parse_env(env_path.read_text(encoding="utf-8"))
        if readback.get("HASS_TOKEN") != new_token:
            raise RuntimeError("Hermes env read-back did not contain the replacement token")
        verify_private_path(env_path, directory=False)
        verify_private_path(pending_path, directory=False)
    except BaseException:
        _private_atomic_write(env_path, old_text)
        pending_path.unlink(missing_ok=True)
        raise

    return {
        "installed": True,
        "old_token_baseline_status": old_status,
        "new_token_status": new_status,
        "env_private": True,
        "rollback_private": True,
        "clipboard_cleared": True,
        "pending_path": str(pending_path),
    }


def finalize_rotation(env_path: Path, pending_path: Path) -> dict[str, object]:
    if not env_path.is_file():
        raise RuntimeError(f"Hermes env file does not exist: {env_path}")
    if not pending_path.is_file():
        raise RuntimeError(
            f"Pending Home Assistant rotation state does not exist: {pending_path}"
        )

    secure_private_path(env_path, directory=False)
    secure_private_path(pending_path, directory=False)
    _, current = _parse_env(env_path.read_text(encoding="utf-8"))
    _, previous = _parse_env(pending_path.read_text(encoding="utf-8"))
    new_token = current.get("HASS_TOKEN", "")
    old_token = previous.get("HASS_TOKEN", "")
    base_url = current.get("HASS_URL", "")
    if len(new_token) < 64 or len(old_token) < 64:
        raise RuntimeError("Current or previous Home Assistant token is missing or malformed")
    if new_token == old_token:
        raise RuntimeError("Current and previous Home Assistant tokens are identical")

    new_status = _api_status(base_url, new_token)
    old_status = _api_status(base_url, old_token)
    if new_status != 200:
        raise RuntimeError(
            f"Replacement Home Assistant token failed with HTTP {new_status}"
        )
    if old_status not in {401, 403}:
        raise RuntimeError(
            f"Previous Home Assistant token is still authorized with HTTP {old_status}"
        )

    pending_path.unlink()
    if pending_path.exists():
        raise RuntimeError("Could not remove pending Home Assistant rotation state")
    return {
        "finalized": True,
        "new_token_status": new_status,
        "old_token_status": old_status,
        "old_token_revoked": True,
        "rollback_removed": True,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--env",
        type=Path,
        default=REPO_ROOT / ".hermes" / ".env",
    )
    parser.add_argument(
        "--pending",
        type=Path,
        default=(
            REPO_ROOT
            / ".hermes"
            / "recovery"
            / "credential-rotation"
            / "ha-env-before-token-rotation.pending"
        ),
    )
    parser.add_argument(
        "--finalize",
        action="store_true",
        help="verify old-token revocation and remove the private rollback copy",
    )
    args = parser.parse_args()
    try:
        result = (
            finalize_rotation(args.env, args.pending)
            if args.finalize
            else install_from_clipboard(args.env, args.pending)
        )
    except Exception as exc:
        print(json.dumps({"installed": False, "error": str(exc)}))
        return 1
    print(json.dumps(result, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
