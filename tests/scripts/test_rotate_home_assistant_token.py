from pathlib import Path

import scripts.rotate_home_assistant_token as rotation
from hermes_security import verify_private_path


OLD_TOKEN = "old." + "o" * 80
NEW_TOKEN = "new." + "n" * 80


def test_install_and_finalize_home_assistant_rotation(tmp_path: Path, monkeypatch):
    env_path = tmp_path / "home" / ".env"
    env_path.parent.mkdir()
    env_path.write_text(
        f"HASS_URL=http://127.0.0.1:8123\nHASS_TOKEN={OLD_TOKEN}\n",
        encoding="utf-8",
    )
    pending_path = tmp_path / "recovery" / "ha.pending"
    cleared: list[bool] = []
    monkeypatch.setattr(rotation, "_read_clipboard", lambda: NEW_TOKEN)
    monkeypatch.setattr(rotation, "_clear_clipboard", lambda: cleared.append(True))
    monkeypatch.setattr(rotation, "_api_status", lambda _url, _token: 200)

    installed = rotation.install_from_clipboard(env_path, pending_path)

    assert installed["installed"] is True
    assert cleared == [True]
    assert NEW_TOKEN in env_path.read_text(encoding="utf-8")
    assert OLD_TOKEN in pending_path.read_text(encoding="utf-8")
    verify_private_path(env_path, directory=False)
    verify_private_path(pending_path, directory=False)

    monkeypatch.setattr(
        rotation,
        "_api_status",
        lambda _url, token: 200 if token == NEW_TOKEN else 401,
    )
    finalized = rotation.finalize_rotation(env_path, pending_path)

    assert finalized["old_token_revoked"] is True
    assert finalized["rollback_removed"] is True
    assert not pending_path.exists()
