#!/usr/bin/env python3
"""Safely rotate the shared Hermes GitHub token from the Windows clipboard.

The replacement token never appears in argv or output.  The script validates
the current and replacement credentials against GitHub, stores a private
rollback copy, atomically updates the canonical default profile, and clears the
clipboard.  Use ``--finalize`` only after the previous token has been revoked.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
from pathlib import Path
from urllib.error import HTTPError, URLError
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

_FINE_GRAINED_TOKEN = re.compile(r"^github_pat_[A-Za-z0-9_]{50,}$")


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


def _github_get(token: str, path: str) -> tuple[int, dict[str, object]]:
    request = Request(
        f"https://api.github.com{path}",
        headers={
            "Accept": "application/vnd.github+json",
            "Authorization": f"Bearer {token}",
            "User-Agent": "Hermes-credential-rotation",
            "X-GitHub-Api-Version": "2022-11-28",
        },
    )
    try:
        with urlopen(request, timeout=20) as response:  # noqa: S310 - fixed HTTPS host
            payload = json.loads(response.read().decode("utf-8"))
            return int(response.status), payload if isinstance(payload, dict) else {}
    except HTTPError as exc:
        return int(exc.code), {}
    except URLError as exc:
        raise RuntimeError(f"GitHub API is unreachable: {exc.reason}") from exc


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


def install_from_clipboard(
    env_path: Path,
    pending_path: Path,
    *,
    expected_owner: str,
    repository: str,
) -> dict[str, object]:
    if not env_path.is_file():
        raise RuntimeError(f"Hermes env file does not exist: {env_path}")
    if pending_path.exists():
        raise RuntimeError(
            "A pending GitHub rotation already exists; finish or roll it back first"
        )

    secure_private_path(env_path, directory=False)
    old_text = env_path.read_text(encoding="utf-8")
    lines, values = _parse_env(old_text)
    old_token = values.get("GITHUB_TOKEN", "")
    if len(old_token) < 40:
        raise RuntimeError("Existing GITHUB_TOKEN is missing or malformed")

    try:
        new_token = _read_clipboard()
    finally:
        _clear_clipboard()
    if not _FINE_GRAINED_TOKEN.fullmatch(new_token):
        raise RuntimeError(
            "Clipboard does not contain one valid-looking fine-grained GitHub token"
        )
    if new_token == old_token:
        raise RuntimeError(
            "Clipboard contains the existing GitHub token, not a replacement"
        )

    old_status, _old_user = _github_get(old_token, "/user")
    new_status, new_user = _github_get(new_token, "/user")
    repo_status, _repo = _github_get(new_token, f"/repos/{repository}")
    login = str(new_user.get("login", ""))
    if old_status != 200:
        raise RuntimeError(
            f"Existing GitHub token baseline failed with HTTP {old_status}"
        )
    if new_status != 200:
        raise RuntimeError(f"Replacement GitHub token failed with HTTP {new_status}")
    if login.casefold() != expected_owner.casefold():
        raise RuntimeError("Replacement GitHub token belongs to an unexpected account")
    if repo_status != 200:
        raise RuntimeError(
            f"Replacement GitHub token cannot read the required repository (HTTP {repo_status})"
        )

    secure_private_directory(pending_path.parent)
    _private_atomic_write(pending_path, old_text)
    try:
        new_text = _replace_env_value(lines, "GITHUB_TOKEN", new_token)
        _private_atomic_write(env_path, new_text)
        _, readback = _parse_env(env_path.read_text(encoding="utf-8"))
        if readback.get("GITHUB_TOKEN") != new_token:
            raise RuntimeError("Hermes env read-back did not contain the replacement token")
        verify_private_path(env_path, directory=False)
        verify_private_path(pending_path, directory=False)
    except BaseException:
        _private_atomic_write(env_path, old_text)
        pending_path.unlink(missing_ok=True)
        raise

    return {
        "installed": True,
        "account_verified": True,
        "repository_verified": True,
        "old_token_baseline_status": old_status,
        "new_token_status": new_status,
        "repository_status": repo_status,
        "env_private": True,
        "rollback_private": True,
        "clipboard_cleared": True,
        "pending_path": str(pending_path),
    }


def finalize_rotation(
    env_path: Path,
    pending_path: Path,
    *,
    expected_owner: str,
) -> dict[str, object]:
    if not env_path.is_file():
        raise RuntimeError(f"Hermes env file does not exist: {env_path}")
    if not pending_path.is_file():
        raise RuntimeError(f"Pending GitHub rotation state does not exist: {pending_path}")

    secure_private_path(env_path, directory=False)
    secure_private_path(pending_path, directory=False)
    _, current = _parse_env(env_path.read_text(encoding="utf-8"))
    _, previous = _parse_env(pending_path.read_text(encoding="utf-8"))
    new_token = current.get("GITHUB_TOKEN", "")
    old_token = previous.get("GITHUB_TOKEN", "")
    if len(new_token) < 40 or len(old_token) < 40:
        raise RuntimeError("Current or previous GitHub token is missing or malformed")
    if new_token == old_token:
        raise RuntimeError("Current and previous GitHub tokens are identical")

    new_status, new_user = _github_get(new_token, "/user")
    old_status, _old_user = _github_get(old_token, "/user")
    if new_status != 200:
        raise RuntimeError(f"Replacement GitHub token failed with HTTP {new_status}")
    if str(new_user.get("login", "")).casefold() != expected_owner.casefold():
        raise RuntimeError("Replacement GitHub token belongs to an unexpected account")
    if old_status not in {401, 403}:
        raise RuntimeError(
            f"Previous GitHub token is still authorized with HTTP {old_status}"
        )

    pending_path.unlink()
    if pending_path.exists():
        raise RuntimeError("Could not remove pending GitHub rotation state")
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
            / "github-env-before-token-rotation.pending"
        ),
    )
    parser.add_argument("--expected-owner", default="hicklax13")
    parser.add_argument("--repository", default="hicklax13/hermes-agent")
    parser.add_argument(
        "--finalize",
        action="store_true",
        help="verify old-token revocation and remove the private rollback copy",
    )
    args = parser.parse_args()
    try:
        if args.finalize:
            result = finalize_rotation(
                args.env,
                args.pending,
                expected_owner=args.expected_owner,
            )
        else:
            result = install_from_clipboard(
                args.env,
                args.pending,
                expected_owner=args.expected_owner,
                repository=args.repository,
            )
    except Exception as exc:
        print(json.dumps({"installed": False, "error": str(exc)}))
        return 1
    print(json.dumps(result, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
