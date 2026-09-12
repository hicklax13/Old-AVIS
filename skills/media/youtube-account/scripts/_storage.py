"""Private, atomic storage helpers for the YouTube account skill."""

from __future__ import annotations

import getpass
import json
import os
import subprocess
import tempfile
from pathlib import Path
from typing import Any


HERMES_HOME = Path(os.environ.get("HERMES_HOME", Path.home() / ".hermes"))


def secure_file(path: Path) -> None:
    if os.name != "nt":
        path.chmod(0o600)
        return

    domain = os.environ.get("USERDOMAIN", "").strip()
    username = os.environ.get("USERNAME", getpass.getuser()).strip()
    identity = f"{domain}\\{username}" if domain else username
    result = subprocess.run(
        [
            "icacls",
            str(path),
            "/inheritance:r",
            "/grant:r",
            f"{identity}:F",
            "NT AUTHORITY\\SYSTEM:F",
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        raise RuntimeError(f"Could not protect private YouTube state at {path}")


def write_private_json(path: Path, payload: dict[str, Any]) -> None:
    """Atomically replace *path* with a user/SYSTEM-only JSON file."""
    path.parent.mkdir(parents=True, exist_ok=True)
    file_descriptor, temporary_name = tempfile.mkstemp(
        prefix=f".{path.name}.",
        suffix=".tmp",
        dir=path.parent,
    )
    os.close(file_descriptor)
    temporary_path = Path(temporary_name)
    try:
        # Protect the empty file before any credential bytes are written.
        secure_file(temporary_path)
        with temporary_path.open("w", encoding="utf-8", newline="\n") as handle:
            json.dump(payload, handle, indent=2)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary_path, path)
        secure_file(path)
    finally:
        temporary_path.unlink(missing_ok=True)


def read_json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"Expected a JSON object at {path}")
    return payload


def credentials_payload(
    credentials: Any,
    *,
    previous: dict[str, Any] | None = None,
) -> dict:
    """Serialize credentials without dropping a working refresh token/scope."""
    payload = json.loads(credentials.to_json())
    old = previous or {}
    if not payload.get("refresh_token") and old.get("refresh_token"):
        payload["refresh_token"] = old["refresh_token"]
    if not payload.get("scopes"):
        old_scopes = old.get("scopes") or old.get("scope")
        if isinstance(old_scopes, str):
            old_scopes = old_scopes.split()
        if old_scopes:
            payload["scopes"] = list(old_scopes)
    if not payload.get("type"):
        payload["type"] = "authorized_user"
    return payload
