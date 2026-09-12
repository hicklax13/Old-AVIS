"""Secure profile-scoped OAuth setup for read-only YouTube account access."""

from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
import time
import urllib.request
import webbrowser
from http.server import BaseHTTPRequestHandler, HTTPServer
from importlib.metadata import version as distribution_version
from pathlib import Path
from secrets import compare_digest
from typing import Callable
from urllib.parse import parse_qs, urlsplit


SCRIPTS_DIR = Path(__file__).resolve().parent
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

from _storage import (  # noqa: E402
    HERMES_HOME,
    credentials_payload,
    read_json,
    write_private_json,
)


SCOPES = ["https://www.googleapis.com/auth/youtube.readonly"]
CLIENT_PATH = HERMES_HOME / "youtube_client_secret.json"
TOKEN_PATH = HERMES_HOME / "youtube_token.json"
LEGACY_PENDING_PATH = HERMES_HOME / "youtube_oauth_pending.json"
REQUIREMENTS_PATH = SCRIPTS_DIR / "requirements.txt"
CALLBACK_PATH = "/oauth2/callback"
DEFAULT_AUTH_TIMEOUT_SECONDS = 300


class OAuthCallbackError(RuntimeError):
    """The loopback callback was incomplete or rejected."""


class OAuthStateError(OAuthCallbackError):
    """The callback failed mandatory state validation."""


class OAuthAuthorizationError(RuntimeError):
    """Google denied authorization or the exchange failed."""


class OAuthTimeoutError(RuntimeError):
    """No valid loopback callback arrived before the deadline."""


class BrowserLaunchError(RuntimeError):
    """The system browser could not be opened."""


def _pinned_requirements() -> list[str]:
    requirements = [
        line.strip()
        for line in REQUIREMENTS_PATH.read_text(encoding="utf-8").splitlines()
        if line.strip() and not line.lstrip().startswith("#")
    ]
    if not requirements or any("==" not in requirement for requirement in requirements):
        raise RuntimeError("YouTube dependency manifest must contain exact version pins")
    return requirements


def _missing_requirements() -> list[str]:
    missing: list[str] = []
    for requirement in _pinned_requirements():
        name, wanted = requirement.split("==", 1)
        try:
            if distribution_version(name) != wanted:
                missing.append(requirement)
        except Exception:
            missing.append(requirement)
    return missing


def install_dependencies() -> bool:
    missing = _missing_requirements()
    if not missing:
        print("Dependencies already installed.")
        return True

    try:
        subprocess.run(
            [
                sys.executable,
                "-m",
                "pip",
                "install",
                "--quiet",
                "--requirement",
                str(REQUIREMENTS_PATH),
            ],
            check=True,
            stdout=subprocess.DEVNULL,
        )
    except (OSError, subprocess.CalledProcessError):
        uv = shutil.which("uv")
        if not uv:
            return False
        try:
            subprocess.run(
                [
                    uv,
                    "pip",
                    "install",
                    "--python",
                    sys.executable,
                    "--quiet",
                    "--requirement",
                    str(REQUIREMENTS_PATH),
                ],
                check=True,
                stdout=subprocess.DEVNULL,
            )
        except (OSError, subprocess.CalledProcessError):
            return False
    return not _missing_requirements()


def _ensure_dependencies() -> None:
    if _missing_requirements() and not install_dependencies():
        raise RuntimeError(
            "Pinned Google API dependencies are unavailable; run --install-deps"
        )


def _client_payload(path: Path) -> dict:
    payload = read_json(path)
    client = payload.get("installed")
    if not isinstance(client, dict):
        raise ValueError(
            "Expected a Google OAuth client JSON whose application type is Desktop app"
        )
    if not client.get("client_id") or not client.get("client_secret"):
        raise ValueError("OAuth client JSON is missing client_id or client_secret")
    return payload


def store_client(source: str) -> None:
    payload = _client_payload(Path(source).expanduser().resolve())
    write_private_json(CLIENT_PATH, payload)
    print(f"OK: YouTube OAuth client saved to {CLIENT_PATH}")


def _credentials():
    _ensure_dependencies()
    from google.oauth2.credentials import Credentials

    return Credentials.from_authorized_user_file(str(TOKEN_PATH))


def check() -> bool:
    if not TOKEN_PATH.exists():
        print(f"NOT_AUTHENTICATED: No token at {TOKEN_PATH}")
        return False

    _ensure_dependencies()
    from google.auth.transport.requests import Request
    from googleapiclient.discovery import build

    try:
        previous = read_json(TOKEN_PATH)
        credentials = _credentials()
        if credentials.expired and credentials.refresh_token:
            credentials.refresh(Request())
            write_private_json(
                TOKEN_PATH,
                credentials_payload(credentials, previous=previous),
            )
        if not credentials.valid:
            print("NOT_AUTHENTICATED: YouTube token is invalid")
            return False
        granted = set(credentials.scopes or previous.get("scopes") or [])
        if not set(SCOPES).issubset(granted):
            print("NOT_AUTHENTICATED: Token is missing youtube.readonly")
            return False
        (
            build("youtube", "v3", credentials=credentials, cache_discovery=False)
            .channels()
            .list(part="id", mine=True, maxResults=1)
            .execute()
        )
    except Exception as error:
        print(f"NOT_AUTHENTICATED: {type(error).__name__}")
        return False

    print(f"AUTHENTICATED: Read-only YouTube grant is valid at {TOKEN_PATH}")
    return True


def _validate_callback_target(
    request_target: str,
    *,
    expected_state: str,
    redirect_uri: str,
) -> str:
    parsed = urlsplit(request_target)
    if parsed.path != CALLBACK_PATH:
        raise OAuthCallbackError("Unexpected loopback callback path")
    params = parse_qs(parsed.query, keep_blank_values=True)
    provider_errors = params.get("error") or []
    if provider_errors:
        if provider_errors == ["access_denied"]:
            raise OAuthAuthorizationError("Google authorization was cancelled")
        raise OAuthAuthorizationError("Google returned an OAuth authorization error")
    states = params.get("state") or []
    if len(states) != 1 or not states[0] or not compare_digest(states[0], expected_state):
        raise OAuthStateError("OAuth state validation failed")
    codes = params.get("code") or []
    if len(codes) != 1 or not codes[0]:
        raise OAuthCallbackError("OAuth callback did not contain one authorization code")
    return f"{redirect_uri}?{parsed.query}"


class _LoopbackServer(HTTPServer):
    expected_state = ""
    redirect_uri = ""
    authorization_response: str | None = None
    terminal_error: RuntimeError | None = None
    rejected_callback = False


class _LoopbackHandler(BaseHTTPRequestHandler):
    server: _LoopbackServer

    def log_message(self, _format: str, *_args: object) -> None:
        # Never put an OAuth code or state from the request target into logs.
        return

    def _respond(self, status: int, title: str, message: str) -> None:
        body = (
            "<!doctype html><meta charset='utf-8'>"
            f"<title>{title}</title><h2>{title}</h2><p>{message}</p>"
        ).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("Referrer-Policy", "no-referrer")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header(
            "Content-Security-Policy",
            "default-src 'none'; style-src 'unsafe-inline'",
        )
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self) -> None:  # noqa: N802 - BaseHTTPRequestHandler contract
        expected_host = f"127.0.0.1:{self.server.server_port}"
        if self.headers.get("Host") != expected_host:
            self.server.rejected_callback = True
            self._respond(400, "Invalid authorization response", "Return to Hermes and retry.")
            return
        try:
            response = _validate_callback_target(
                self.path,
                expected_state=self.server.expected_state,
                redirect_uri=self.server.redirect_uri,
            )
        except OAuthAuthorizationError as error:
            self.server.terminal_error = error
            self._respond(200, "Authorization cancelled", "You can close this tab.")
            return
        except OAuthCallbackError:
            self.server.rejected_callback = True
            self._respond(400, "Invalid authorization response", "Return to Hermes and retry.")
            return
        self.server.authorization_response = response
        self._respond(200, "Authorization complete", "Return to Hermes. You can close this tab.")


def _open_system_browser(url: str, *, new: int = 1, autoraise: bool = True) -> bool:
    if webbrowser.open(url, new=new, autoraise=autoraise):
        return True
    if os.name == "nt":
        try:
            os.startfile(url)  # type: ignore[attr-defined]
            return True
        except OSError:
            return False
    return False


def _wait_for_callback(server: _LoopbackServer, timeout_seconds: int) -> str:
    deadline = time.monotonic() + timeout_seconds
    server.timeout = 0.5
    while time.monotonic() < deadline:
        server.handle_request()
        if server.authorization_response:
            return server.authorization_response
        if server.terminal_error:
            raise server.terminal_error
    raise OAuthTimeoutError(
        "Authorization timed out; no token changed. Run --authorize to try again"
    )


def _build_flow(redirect_uri: str):
    _ensure_dependencies()
    from google_auth_oauthlib.flow import Flow

    return Flow.from_client_secrets_file(
        str(CLIENT_PATH),
        scopes=SCOPES,
        redirect_uri=redirect_uri,
        autogenerate_code_verifier=True,
    )


def authorize(
    *,
    timeout_seconds: int = DEFAULT_AUTH_TIMEOUT_SECONDS,
    browser_opener: Callable[..., bool] = _open_system_browser,
) -> None:
    if not CLIENT_PATH.exists():
        raise FileNotFoundError("No YouTube OAuth client is stored; run --client-secret first")

    previous = read_json(TOKEN_PATH) if TOKEN_PATH.exists() else {}
    with _LoopbackServer(("127.0.0.1", 0), _LoopbackHandler) as server:
        server.redirect_uri = f"http://127.0.0.1:{server.server_port}{CALLBACK_PATH}"
        flow = _build_flow(server.redirect_uri)
        authorization_url, state = flow.authorization_url(
            access_type="offline",
            prompt="consent",
        )
        if not state or not flow.code_verifier:
            raise RuntimeError("Google OAuth library did not create required PKCE/state data")
        server.expected_state = state
        if not browser_opener(authorization_url, new=1, autoraise=True):
            raise BrowserLaunchError(
                "Could not open the system browser; no token changed. Run --authorize again"
            )
        print("BROWSER_OPENED: Complete Google's read-only YouTube consent in the browser.")
        authorization_response = _wait_for_callback(server, timeout_seconds)

    try:
        flow.fetch_token(authorization_response=authorization_response)
    except Exception as error:
        raise OAuthAuthorizationError(
            "Google token exchange failed; the existing token was preserved"
        ) from error

    payload = credentials_payload(flow.credentials, previous=previous)
    granted = set(payload.get("scopes") or [])
    if not set(SCOPES).issubset(granted):
        raise OAuthAuthorizationError(
            "Google did not grant youtube.readonly; the existing token was preserved"
        )
    if not payload.get("refresh_token"):
        raise OAuthAuthorizationError(
            "Google did not issue persistent access; the existing token was preserved"
        )
    write_private_json(TOKEN_PATH, payload)
    LEGACY_PENDING_PATH.unlink(missing_ok=True)
    print(f"OK: Read-only YouTube token saved to {TOKEN_PATH}")


def revoke() -> None:
    if not TOKEN_PATH.exists():
        LEGACY_PENDING_PATH.unlink(missing_ok=True)
        print("No YouTube token to revoke")
        return

    credentials = _credentials()
    token = credentials.refresh_token or credentials.token
    if token:
        try:
            request = urllib.request.Request(
                "https://oauth2.googleapis.com/revoke",
                data=f"token={token}".encode("utf-8"),
                method="POST",
                headers={"Content-Type": "application/x-www-form-urlencoded"},
            )
            urllib.request.urlopen(request, timeout=15).read()
        except Exception as error:
            print(f"Remote revocation did not complete: {type(error).__name__}")
    TOKEN_PATH.unlink(missing_ok=True)
    LEGACY_PENDING_PATH.unlink(missing_ok=True)
    print("YouTube token deleted")


def _bounded_timeout(value: str) -> int:
    seconds = int(value)
    if not 30 <= seconds <= 900:
        raise argparse.ArgumentTypeError("--timeout must be between 30 and 900 seconds")
    return seconds


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Set up read-only YouTube OAuth")
    actions = parser.add_mutually_exclusive_group(required=True)
    actions.add_argument("--check", action="store_true")
    actions.add_argument("--client-secret", metavar="PATH")
    actions.add_argument("--authorize", action="store_true")
    actions.add_argument("--revoke", action="store_true")
    actions.add_argument("--install-deps", action="store_true")
    parser.add_argument(
        "--timeout",
        type=_bounded_timeout,
        default=DEFAULT_AUTH_TIMEOUT_SECONDS,
        help="Seconds to wait for the protected loopback callback (30-900)",
    )
    return parser


def main() -> None:
    args = _build_parser().parse_args()
    try:
        if args.check:
            raise SystemExit(0 if check() else 1)
        if args.client_secret:
            store_client(args.client_secret)
        elif args.authorize:
            authorize(timeout_seconds=args.timeout)
        elif args.revoke:
            revoke()
        elif args.install_deps:
            if not install_dependencies():
                raise RuntimeError("Could not install the pinned Google API dependencies")
            print("Dependencies installed")
    except KeyboardInterrupt:
        print("CANCELLED: Authorization stopped; no token changed", file=sys.stderr)
        raise SystemExit(130) from None
    except (FileNotFoundError, RuntimeError, ValueError, json.JSONDecodeError) as error:
        print(f"ERROR: {error}", file=sys.stderr)
        raise SystemExit(1) from None
    except Exception as error:
        print(
            f"ERROR: {type(error).__name__}: operation failed; no token changed",
            file=sys.stderr,
        )
        raise SystemExit(1) from None


if __name__ == "__main__":
    main()
