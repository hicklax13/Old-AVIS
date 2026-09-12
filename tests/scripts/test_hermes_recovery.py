from __future__ import annotations

import io
import json
import os
import sqlite3
import tarfile
from pathlib import Path

import pytest

from scripts import hermes_recovery as recovery


def _plan_dict(tmp_path: Path) -> dict[str, object]:
    age = tmp_path / "age.exe"
    age.write_bytes(b"age")
    hermes_home = tmp_path / "home"
    source = hermes_home / "state"
    source.mkdir(parents=True)
    return {
        "version": 1,
        "age_executable": str(age.resolve()),
        "recipient": "age1zvuq8u68vtpvrjnmev7ezkmn9rpefs2g8qdjptyqmzcy6e9qfpvq80ffw8",
        "hermes_home": str(hermes_home.resolve()),
        "staging_root": str((hermes_home / "recovery" / "staging").resolve()),
        "status_path": str((hermes_home / "recovery" / "status.json").resolve()),
        "destinations": [
            {
                "path": str((tmp_path / "destination").resolve()),
                "retention": 3,
                "required": True,
                "private": False,
            }
        ],
        "sources": [
            {
                "name": "hermes-state",
                "path": str(source.resolve()),
                "kind": "tree",
            }
        ],
    }


def _write_plan(tmp_path: Path, value: dict[str, object]) -> Path:
    path = tmp_path / "plan.json"
    path.write_text(json.dumps(value), encoding="utf-8")
    return path


def test_load_plan_accepts_public_recipient_only(tmp_path: Path) -> None:
    plan = recovery.load_plan(_write_plan(tmp_path, _plan_dict(tmp_path)))

    assert plan.recipient.startswith("age1")
    assert plan.destinations[0].retention == 3
    assert plan.sources[0].name == "hermes-state"


@pytest.mark.parametrize("key", ["identity", "private_key", "password"])
def test_load_plan_rejects_secret_or_unknown_keys(tmp_path: Path, key: str) -> None:
    raw = _plan_dict(tmp_path)
    raw[key] = "must-not-be-here"

    with pytest.raises(recovery.RecoveryError):
        recovery.load_plan(_write_plan(tmp_path, raw))


def test_load_plan_rejects_staging_outside_hermes_home(tmp_path: Path) -> None:
    raw = _plan_dict(tmp_path)
    raw["staging_root"] = str((tmp_path / "outside").resolve())

    with pytest.raises(recovery.RecoveryError, match="child of hermes_home"):
        recovery.load_plan(_write_plan(tmp_path, raw))


def test_copy_tree_snapshots_sqlite_and_prunes_regeneratable_state(tmp_path: Path) -> None:
    source = tmp_path / "source"
    source.mkdir()
    database = source / "state.sqlite"
    connection = sqlite3.connect(database)
    connection.execute("CREATE TABLE evidence (value TEXT NOT NULL)")
    connection.execute("INSERT INTO evidence VALUES ('restorable')")
    connection.commit()
    connection.close()
    (source / "config.yaml").write_text("enabled: true\n", encoding="utf-8")
    (source / "agent.log").write_text("not recovery state", encoding="utf-8")
    (source / "node_modules").mkdir()
    (source / "node_modules" / "dependency.js").write_text("generated", encoding="utf-8")
    destination = tmp_path / "destination"

    detail = recovery._copy_tree(source, destination)

    assert detail["sqlite_snapshots"] == 1
    assert (destination / "config.yaml").is_file()
    assert not (destination / "agent.log").exists()
    assert not (destination / "node_modules").exists()
    restored = sqlite3.connect(destination / "state.sqlite")
    assert restored.execute("SELECT value FROM evidence").fetchone() == ("restorable",)
    restored.close()


def test_safe_extract_rejects_path_traversal(tmp_path: Path) -> None:
    archive_path = tmp_path / "malicious.tar.gz"
    with tarfile.open(archive_path, "w:gz") as archive:
        member = tarfile.TarInfo("../escaped.txt")
        payload = b"escaped"
        member.size = len(payload)
        archive.addfile(member, io.BytesIO(payload))

    with pytest.raises(recovery.RecoveryError, match="Unsafe archive member"):
        recovery._safe_extract(archive_path, tmp_path / "restore")

    assert not (tmp_path / "escaped.txt").exists()


def test_verify_restored_payload_detects_tampering(tmp_path: Path) -> None:
    restore = tmp_path / "restore"
    payload = restore / "payload"
    payload.mkdir(parents=True)
    file_path = payload / "config.yaml"
    file_path.write_text("safe: true\n", encoding="utf-8")
    manifest = recovery._manifest_for_payload(
        payload,
        run_id="abc",
        started_at="2026-08-31T00:00:00Z",
        completed_at="2026-08-31T00:00:01Z",
        full=False,
        source_records=[],
    )
    (restore / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
    file_path.write_text("tampered: true\n", encoding="utf-8")

    with pytest.raises(recovery.RecoveryError, match="hash mismatch"):
        recovery._verify_restored_payload(restore)


def test_retention_only_prunes_valid_old_recovery_archives(tmp_path: Path) -> None:
    destination = recovery.Destination(tmp_path, retention=2, required=True, private=False)
    names = [
        "hermes-recovery-20260829T010101Z-11111111.tar.gz.age",
        "hermes-recovery-20260830T010101Z-22222222.tar.gz.age",
        "hermes-recovery-20260831T010101Z-33333333.tar.gz.age",
    ]
    for index, name in enumerate(names):
        path = tmp_path / name
        path.write_bytes(name.encode())
        os.utime(path, ns=(index + 1, index + 1))
        path.with_suffix(path.suffix + ".json").write_text("{}", encoding="utf-8")
    unrelated = tmp_path / "do-not-delete.age"
    unrelated.write_text("keep", encoding="utf-8")

    removed = recovery._apply_retention(destination)

    assert removed == [names[0]]
    assert unrelated.is_file()
    assert not (tmp_path / names[0]).exists()
    assert (tmp_path / names[1]).is_file()
    assert (tmp_path / names[2]).is_file()


def test_desktop_copy_uses_explicit_allowlist(tmp_path: Path) -> None:
    source = tmp_path / "desktop"
    source.mkdir()
    (source / "connections.json").write_text("{}", encoding="utf-8")
    (source / "Preferences").write_text("browser internals", encoding="utf-8")
    (source / "Local Storage").mkdir()
    (source / "Local Storage" / "state").write_text("live leveldb", encoding="utf-8")

    detail = recovery._copy_desktop_state(source, tmp_path / "copy")

    assert detail["files"] == 1
    assert (tmp_path / "copy" / "connections.json").is_file()
    assert not (tmp_path / "copy" / "Preferences").exists()
    assert not (tmp_path / "copy" / "Local Storage").exists()


def test_restore_identity_allows_inheritance_from_private_key_directory(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    raw = _plan_dict(tmp_path)
    plan = recovery.load_plan(_write_plan(tmp_path, raw))
    archive = tmp_path / "hermes-recovery-20260831T010101Z-12345678.tar.gz.age"
    archive.write_bytes(b"ciphertext")
    identity = tmp_path / "identity.txt"
    identity.write_text("private", encoding="utf-8")
    observed: list[bool] = []

    def fake_verify(_path: Path, *, directory: bool, require_protected: bool) -> None:
        assert directory is False
        observed.append(require_protected)
        raise recovery.RecoveryError("stop after ACL assertion")

    monkeypatch.setattr(recovery, "verify_private_path", fake_verify)

    with pytest.raises(recovery.RecoveryError, match="stop after ACL assertion"):
        recovery.restore_archive(
            plan,
            archive_path=archive,
            identity_path=identity,
            destination=tmp_path / "restore",
        )

    assert observed == [False]


def test_identity_path_is_absolutized_without_resolving_reparse_points(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    identity = tmp_path / "Personal Vault" / "identity.txt"

    def fail_resolve(*_args, **_kwargs):
        raise AssertionError("identity path must not call Path.resolve")

    monkeypatch.setattr(Path, "resolve", fail_resolve)

    result = recovery._lexical_absolute(identity)

    assert result.is_absolute()
    assert result.name == "identity.txt"
