from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path
from threading import Thread
from types import SimpleNamespace
from urllib.request import urlopen
from urllib.parse import urlencode

import pytest


ROOT = Path(__file__).resolve().parents[2]
SCRIPTS = ROOT / "skills" / "media" / "youtube-account" / "scripts"


def _load_module(filename: str, name: str):
    if str(SCRIPTS) not in sys.path:
        sys.path.insert(0, str(SCRIPTS))
    spec = importlib.util.spec_from_file_location(name, SCRIPTS / filename)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture
def setup_module():
    return _load_module("setup.py", "youtube_account_setup_test")


def test_dependency_manifest_uses_only_exact_pins(setup_module):
    requirements = setup_module._pinned_requirements()

    assert requirements
    assert all(requirement.count("==") == 1 for requirement in requirements)
    assert not any(">=" in requirement or "~=" in requirement for requirement in requirements)


def test_callback_requires_exact_state_and_single_code(setup_module):
    callback = (
        f"{setup_module.CALLBACK_PATH}?"
        f"{urlencode({'code': 'one', 'state': 'expected'})}"
    )

    response = setup_module._validate_callback_target(
        callback,
        expected_state="expected",
        redirect_uri="http://127.0.0.1:43123/oauth2/callback",
    )

    assert response.startswith("http://127.0.0.1:43123/oauth2/callback?")
    with pytest.raises(setup_module.OAuthStateError):
        setup_module._validate_callback_target(
            f"{setup_module.CALLBACK_PATH}?code=one",
            expected_state="expected",
            redirect_uri="http://127.0.0.1:43123/oauth2/callback",
        )
    with pytest.raises(setup_module.OAuthStateError):
        setup_module._validate_callback_target(
            f"{setup_module.CALLBACK_PATH}?code=one&state=wrong",
            expected_state="expected",
            redirect_uri="http://127.0.0.1:43123/oauth2/callback",
        )


def test_ephemeral_loopback_server_accepts_valid_callback(setup_module):
    with setup_module._LoopbackServer(
        ("127.0.0.1", 0), setup_module._LoopbackHandler
    ) as server:
        server.expected_state = "expected"
        server.redirect_uri = (
            f"http://127.0.0.1:{server.server_port}{setup_module.CALLBACK_PATH}"
        )
        worker = Thread(target=server.handle_request, daemon=True)
        worker.start()

        with urlopen(
            f"{server.redirect_uri}?{urlencode({'code': 'in-memory', 'state': 'expected'})}",
            timeout=2,
        ) as response:
            assert response.status == 200
        worker.join(timeout=2)

        assert not worker.is_alive()
        assert server.authorization_response == (
            f"{server.redirect_uri}?code=in-memory&state=expected"
        )


def test_client_file_must_be_a_desktop_app(setup_module, tmp_path):
    client = tmp_path / "client.json"
    client.write_text(
        json.dumps({"web": {"client_id": "id", "client_secret": "secret"}}),
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="Desktop app"):
        setup_module._client_payload(client)


def test_authorize_keeps_code_in_memory_and_writes_only_after_exchange(
    setup_module, monkeypatch, tmp_path
):
    client_path = tmp_path / "client.json"
    token_path = tmp_path / "token.json"
    client_path.write_text("{}", encoding="utf-8")
    monkeypatch.setattr(setup_module, "CLIENT_PATH", client_path)
    monkeypatch.setattr(setup_module, "TOKEN_PATH", token_path)
    monkeypatch.setattr(setup_module, "LEGACY_PENDING_PATH", tmp_path / "pending.json")

    fetched: dict[str, str] = {}

    class FakeCredentials:
        scopes = setup_module.SCOPES

        def to_json(self):
            return json.dumps(
                {
                    "token": "access",
                    "refresh_token": "refresh",
                    "client_id": "client",
                    "client_secret": "secret",
                    "scopes": setup_module.SCOPES,
                }
            )

    class FakeFlow:
        code_verifier = "pkce-verifier"
        credentials = FakeCredentials()

        def authorization_url(self, **_kwargs):
            return (
                "https://accounts.google.com/o/oauth2/v2/auth?state=expected",
                "expected",
            )

        def fetch_token(self, *, authorization_response):
            fetched["authorization_response"] = authorization_response

    monkeypatch.setattr(setup_module, "_build_flow", lambda _redirect: FakeFlow())
    monkeypatch.setattr(
        setup_module,
        "_wait_for_callback",
        lambda server, _timeout: (
            f"{server.redirect_uri}?code=in-memory-only&state={server.expected_state}"
        ),
    )
    written: dict[str, object] = {}
    monkeypatch.setattr(
        setup_module,
        "write_private_json",
        lambda path, payload: written.update(path=str(path), payload=payload),
    )

    opened: list[str] = []
    setup_module.authorize(
        timeout_seconds=30,
        browser_opener=lambda url, **_kwargs: not opened.append(url),
    )

    assert opened == ["https://accounts.google.com/o/oauth2/v2/auth?state=expected"]
    assert "code=in-memory-only" in fetched["authorization_response"]
    assert written["path"] == str(token_path)
    assert written["payload"]["refresh_token"] == "refresh"


def test_cancelled_authorization_preserves_existing_token(
    setup_module, monkeypatch, tmp_path
):
    client_path = tmp_path / "client.json"
    token_path = tmp_path / "token.json"
    client_path.write_text("{}", encoding="utf-8")
    existing_token = '{"refresh_token":"working-token"}'
    token_path.write_text(existing_token, encoding="utf-8")
    monkeypatch.setattr(setup_module, "CLIENT_PATH", client_path)
    monkeypatch.setattr(setup_module, "TOKEN_PATH", token_path)

    flow = SimpleNamespace(
        code_verifier="pkce-verifier",
        authorization_url=lambda **_kwargs: (
            "https://accounts.google.com/auth",
            "expected",
        ),
    )
    monkeypatch.setattr(setup_module, "_build_flow", lambda _redirect: flow)
    monkeypatch.setattr(
        setup_module,
        "_wait_for_callback",
        lambda _server, _timeout: (_ for _ in ()).throw(
            setup_module.OAuthAuthorizationError("cancelled")
        ),
    )

    with pytest.raises(setup_module.OAuthAuthorizationError):
        setup_module.authorize(
            timeout_seconds=30,
            browser_opener=lambda _url, **_kwargs: True,
        )

    assert token_path.read_text(encoding="utf-8") == existing_token


def test_private_json_is_secured_before_and_after_atomic_replace(monkeypatch, tmp_path):
    storage = _load_module("_storage.py", "youtube_account_storage_test")
    secured: list[Path] = []
    monkeypatch.setattr(storage, "secure_file", lambda path: secured.append(Path(path)))
    target = tmp_path / "youtube_token.json"

    storage.write_private_json(target, {"refresh_token": "secret"})

    assert json.loads(target.read_text(encoding="utf-8"))["refresh_token"] == "secret"
    assert len(secured) == 2
    assert secured[-1] == target


def test_removed_manual_code_flag_is_not_accepted(setup_module):
    with pytest.raises(SystemExit) as exc:
        setup_module._build_parser().parse_args(["--auth-code", "secret"])

    assert exc.value.code == 2
