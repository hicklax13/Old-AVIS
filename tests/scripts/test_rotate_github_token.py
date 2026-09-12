from pathlib import Path

import pytest

import scripts.rotate_github_token as rotation
from hermes_security import verify_private_path


OLD_TOKEN = "ghp_" + "o" * 64
NEW_TOKEN = "github_pat_" + "n" * 80


def _github_ok(token: str, path: str) -> tuple[int, dict[str, object]]:
    if path == "/user":
        return 200, {"login": "hicklax13"}
    if path == "/repos/hicklax13/hermes-agent" and token == NEW_TOKEN:
        return 200, {"full_name": "hicklax13/hermes-agent"}
    return 404, {}


def test_install_and_finalize_github_rotation_without_exposing_tokens(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
):
    env_path = tmp_path / "home" / ".env"
    env_path.parent.mkdir()
    env_path.write_text(f"GITHUB_TOKEN={OLD_TOKEN}\nOTHER=value\n", encoding="utf-8")
    pending_path = tmp_path / "recovery" / "github.pending"
    cleared: list[bool] = []
    monkeypatch.setattr(rotation, "_read_clipboard", lambda: NEW_TOKEN)
    monkeypatch.setattr(rotation, "_clear_clipboard", lambda: cleared.append(True))
    monkeypatch.setattr(rotation, "_github_get", _github_ok)

    installed = rotation.install_from_clipboard(
        env_path,
        pending_path,
        expected_owner="hicklax13",
        repository="hicklax13/hermes-agent",
    )

    assert installed["installed"] is True
    assert cleared == [True]
    assert NEW_TOKEN in env_path.read_text(encoding="utf-8")
    assert OLD_TOKEN not in env_path.read_text(encoding="utf-8")
    assert OLD_TOKEN in pending_path.read_text(encoding="utf-8")
    verify_private_path(env_path, directory=False)
    verify_private_path(pending_path, directory=False)

    def revoked_get(token: str, path: str) -> tuple[int, dict[str, object]]:
        assert path == "/user"
        if token == NEW_TOKEN:
            return 200, {"login": "hicklax13"}
        return 401, {}

    monkeypatch.setattr(rotation, "_github_get", revoked_get)
    finalized = rotation.finalize_rotation(
        env_path,
        pending_path,
        expected_owner="hicklax13",
    )

    assert finalized["old_token_revoked"] is True
    assert finalized["rollback_removed"] is True
    assert not pending_path.exists()


def test_unexpected_github_account_fails_before_env_write_and_clears_clipboard(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
):
    env_path = tmp_path / ".env"
    original = f"GITHUB_TOKEN={OLD_TOKEN}\n"
    env_path.write_text(original, encoding="utf-8")
    pending_path = tmp_path / "recovery" / "github.pending"
    cleared: list[bool] = []
    monkeypatch.setattr(rotation, "_read_clipboard", lambda: NEW_TOKEN)
    monkeypatch.setattr(rotation, "_clear_clipboard", lambda: cleared.append(True))

    def wrong_account(token: str, path: str) -> tuple[int, dict[str, object]]:
        if path == "/user":
            return 200, {"login": "someone-else" if token == NEW_TOKEN else "hicklax13"}
        return 200, {}

    monkeypatch.setattr(rotation, "_github_get", wrong_account)

    with pytest.raises(RuntimeError, match="unexpected account"):
        rotation.install_from_clipboard(
            env_path,
            pending_path,
            expected_owner="hicklax13",
            repository="hicklax13/hermes-agent",
        )

    assert cleared == [True]
    assert env_path.read_text(encoding="utf-8") == original
    assert not pending_path.exists()
