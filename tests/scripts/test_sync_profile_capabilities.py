import os
import shutil
from pathlib import Path

import pytest
import yaml

import scripts.sync_profile_capabilities as sync_module
from hermes_security import is_reparse_point, verify_private_tree
from scripts.sync_profile_capabilities import SyncError, synchronize


def _write_profile(
    path: Path,
    *,
    mcp: dict,
    env: str,
    skill: str,
    token: bool = False,
) -> None:
    path.mkdir(parents=True)
    (path / "config.yaml").write_text(
        yaml.safe_dump(
            {
                "model": {"provider": "test", "default": path.name},
                "mcp_servers": mcp,
                "platform_toolsets": {"cli": [f"tool-{path.name}"]},
                "plugins": {"enabled": [f"plugin-{path.name}"], "disabled": []},
            },
            sort_keys=False,
        ),
        encoding="utf-8",
    )
    (path / ".env").write_text(env, encoding="utf-8")
    skill_dir = path / "skills" / skill
    skill_dir.mkdir(parents=True)
    (skill_dir / "SKILL.md").write_text(f"---\nname: {skill}\n---\n", encoding="utf-8")
    if token:
        (skill_dir / "account_token.json").write_text("secret", encoding="utf-8")


def test_sync_uses_default_static_keys_and_migrates_service_local_secrets(tmp_path: Path):
    root = tmp_path / "home"
    _write_profile(
        root,
        mcp={"alpha": {"url": "https://alpha.example/mcp", "auth": "oauth"}},
        env=(
            "OPENAI_API_KEY=one\n"
            "ANTHROPIC_API_KEY=two\n"
            "TELEGRAM_BOT_TOKEN=default-bot\n"
            "TERMINAL_TIMEOUT=60\n"
        ),
        skill="alpha-skill",
        token=True,
    )
    beta = root / "profiles" / "beta"
    _write_profile(
        beta,
        mcp={"beta": {"url": "https://beta.example/mcp", "enabled": False}},
        env=(
            "OPENAI_API_KEY=one\n"
            "TELEGRAM_BOT_TOKEN=stale-copied-bot\n"
            "TERMINAL_TIMEOUT=90\n"
        ),
        skill="beta-skill",
        token=True,
    )

    dry_run = synchronize(root, apply=False)

    assert dry_run.changed_configs == ["beta", "default"]
    assert dry_run.changed_envs == ["beta"]
    assert dry_run.removed_service_local == {"beta": ["TELEGRAM_BOT_TOKEN"]}
    assert dry_run.env_keys == ["ANTHROPIC_API_KEY", "OPENAI_API_KEY"]
    assert (root / "skills" / "beta-skill").exists() is False

    report = synchronize(root, apply=True)

    assert report.backup_dir is not None
    for profile in (root, beta):
        cfg = yaml.safe_load((profile / "config.yaml").read_text(encoding="utf-8"))
        assert set(cfg["mcp_servers"]) == {"alpha", "beta"}
        assert all(entry["enabled"] is True for entry in cfg["mcp_servers"].values())
        assert cfg["platform_toolsets"]["cli"] == ["tool-home", "tool-beta"]
        assert cfg["plugins"]["enabled"] == ["plugin-home", "plugin-beta"]
        env_text = (profile / ".env").read_text(encoding="utf-8")
        assert "OPENAI_API_KEY=one" in env_text
        assert "ANTHROPIC_API_KEY=two" in env_text
        assert (profile / "skills" / "alpha-skill" / "SKILL.md").is_file()
        assert (profile / "skills" / "beta-skill" / "SKILL.md").is_file()

    assert "TELEGRAM_BOT_TOKEN=default-bot" in (root / ".env").read_text(encoding="utf-8")
    beta_env = (beta / ".env").read_text(encoding="utf-8")
    assert "TELEGRAM_BOT_TOKEN" not in beta_env
    assert "TERMINAL_TIMEOUT=90" in beta_env
    assert not (root / "skills" / "beta-skill" / "account_token.json").exists()
    assert not (beta / "skills" / "alpha-skill" / "account_token.json").exists()
    verify_private_tree(Path(report.backup_dir))

    clean = synchronize(root, apply=False)
    assert clean.changed_configs == []
    assert clean.changed_envs == []
    assert clean.copied_skills == {}
    assert clean.removed_service_local == {}


def test_sync_preserves_explicit_blocked_mcps_but_enables_unreasoned_entries(
    tmp_path: Path,
):
    """A deliberate inactive classification must survive future all-profile
    syncs, while a bare ``enabled: false`` is still normalized to enabled."""
    root = tmp_path / "home"
    blocked = {
        "url": "https://paid.example/mcp",
        "enabled": False,
        "blocked_reason": "Inactive under the no-paid-services policy.",
    }
    _write_profile(
        root,
        mcp={"paid": blocked},
        env="OPENAI_API_KEY=one\n",
        skill="alpha-skill",
    )
    beta = root / "profiles" / "beta"
    _write_profile(
        beta,
        mcp={
            "paid": blocked,
            "accidentally-off": {
                "url": "https://free.example/mcp",
                "enabled": False,
            },
        },
        env="OPENAI_API_KEY=one\n",
        skill="beta-skill",
    )

    synchronize(root, apply=True)

    for profile in (root, beta):
        servers = yaml.safe_load(
            (profile / "config.yaml").read_text(encoding="utf-8")
        )["mcp_servers"]
        assert servers["paid"]["enabled"] is False
        assert servers["paid"]["blocked_reason"] == blocked["blocked_reason"]
        assert servers["accidentally-off"]["enabled"] is True

    clean = synchronize(root, apply=False)
    assert clean.changed_configs == []


def test_sync_refuses_ambiguous_keys_before_writes(tmp_path: Path):
    root = tmp_path / "home"
    _write_profile(root, mcp={}, env="NEW_VENDOR_API_KEY=one\n", skill="alpha-skill")

    with pytest.raises(SyncError, match="Ambiguous environment keys.*NEW_VENDOR_API_KEY"):
        synchronize(root, apply=True)

    assert not (root / "backups" / "profile-capability-sync").exists()


def test_sync_refuses_conflicting_static_account_keys_before_writes(tmp_path: Path):
    root = tmp_path / "home"
    _write_profile(root, mcp={}, env="OPENAI_API_KEY=one\n", skill="alpha-skill")
    beta = root / "profiles" / "beta"
    _write_profile(beta, mcp={}, env="OPENAI_API_KEY=two\n", skill="beta-skill")
    before = (root / "config.yaml").read_bytes()

    with pytest.raises(SyncError, match="OPENAI_API_KEY"):
        synchronize(root, apply=True)

    assert (root / "config.yaml").read_bytes() == before
    assert not (root / "backups" / "profile-capability-sync").exists()


def test_explicit_default_env_resolution_replaces_conflicts_with_private_backup(
    tmp_path: Path,
):
    root = tmp_path / "home"
    _write_profile(root, mcp={}, env="GITHUB_TOKEN=new\n", skill="alpha-skill")
    beta = root / "profiles" / "beta"
    _write_profile(beta, mcp={}, env="GITHUB_TOKEN=old\n", skill="beta-skill")

    dry_run = synchronize(
        root,
        apply=False,
        resolve_env_conflicts_from_default=True,
    )

    assert dry_run.changed_envs == ["beta"]
    assert "GITHUB_TOKEN=old" in (beta / ".env").read_text(encoding="utf-8")

    report = synchronize(
        root,
        apply=True,
        resolve_env_conflicts_from_default=True,
    )

    assert report.backup_dir is not None
    assert "GITHUB_TOKEN=new" in (beta / ".env").read_text(encoding="utf-8")
    assert "GITHUB_TOKEN=old" in (
        Path(report.backup_dir) / "beta" / ".env"
    ).read_text(encoding="utf-8")
    verify_private_tree(Path(report.backup_dir))


def test_sync_refuses_shared_key_missing_from_default(tmp_path: Path):
    root = tmp_path / "home"
    _write_profile(root, mcp={}, env="TERMINAL_TIMEOUT=60\n", skill="alpha-skill")
    beta = root / "profiles" / "beta"
    _write_profile(beta, mcp={}, env="OPENAI_API_KEY=one\n", skill="beta-skill")

    with pytest.raises(SyncError, match="canonical default.*OPENAI_API_KEY"):
        synchronize(root, apply=True)


def test_sync_refuses_mcp_definition_conflicts(tmp_path: Path):
    root = tmp_path / "home"
    _write_profile(
        root,
        mcp={"shared": {"url": "https://default.example/mcp"}},
        env="OPENAI_API_KEY=one\n",
        skill="alpha-skill",
    )
    beta = root / "profiles" / "beta"
    _write_profile(
        beta,
        mcp={"shared": {"url": "https://beta.example/mcp"}},
        env="OPENAI_API_KEY=one\n",
        skill="beta-skill",
    )

    with pytest.raises(SyncError, match="MCP definition conflicts.*shared"):
        synchronize(root, apply=True)


def test_sync_refuses_skill_definition_conflicts(tmp_path: Path):
    root = tmp_path / "home"
    _write_profile(root, mcp={}, env="OPENAI_API_KEY=one\n", skill="shared-skill")
    beta = root / "profiles" / "beta"
    _write_profile(beta, mcp={}, env="OPENAI_API_KEY=one\n", skill="shared-skill")
    (beta / "skills" / "shared-skill" / "implementation.py").write_text(
        "DIFFERENT = True\n", encoding="utf-8"
    )

    with pytest.raises(SyncError, match="Skill definition conflicts.*shared-skill"):
        synchronize(root, apply=True)


def test_explicit_default_skill_resolution_preserves_profile_local_tokens(tmp_path: Path):
    root = tmp_path / "home"
    _write_profile(root, mcp={}, env="OPENAI_API_KEY=one\n", skill="shared-skill")
    default_skill = root / "skills" / "shared-skill"
    (default_skill / "implementation.py").write_text("CANONICAL = True\n", encoding="utf-8")
    beta = root / "profiles" / "beta"
    _write_profile(
        beta,
        mcp={},
        env="OPENAI_API_KEY=one\n",
        skill="shared-skill",
        token=True,
    )
    beta_skill = beta / "skills" / "shared-skill"
    (beta_skill / "obsolete.py").write_text("OBSOLETE = True\n", encoding="utf-8")

    dry_run = synchronize(
        root,
        apply=False,
        resolve_skill_conflicts_from_default=True,
    )

    assert dry_run.replaced_skills == {"beta": ["shared-skill"]}

    report = synchronize(
        root,
        apply=True,
        resolve_skill_conflicts_from_default=True,
    )

    assert report.backup_dir is not None
    assert (beta_skill / "implementation.py").read_text(encoding="utf-8") == "CANONICAL = True\n"
    assert not (beta_skill / "obsolete.py").exists()
    assert (beta_skill / "account_token.json").read_text(encoding="utf-8") == "secret"
    assert (Path(report.backup_dir) / "beta" / "skills" / "shared-skill" / "obsolete.py").is_file()


def test_sync_rolls_back_files_and_skills_after_mid_apply_failure(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    root = tmp_path / "home"
    _write_profile(
        root,
        mcp={"alpha": {"url": "https://alpha.example/mcp"}},
        env="OPENAI_API_KEY=one\nANTHROPIC_API_KEY=two\n",
        skill="alpha-skill",
    )
    beta = root / "profiles" / "beta"
    _write_profile(
        beta,
        mcp={"beta": {"url": "https://beta.example/mcp"}},
        env="OPENAI_API_KEY=one\n",
        skill="beta-skill",
    )
    originals = {
        path: path.read_bytes()
        for path in (root / "config.yaml", root / ".env", beta / "config.yaml", beta / ".env")
    }
    real_atomic_write = sync_module._atomic_write
    calls = 0

    def fail_once(path: Path, content: bytes, mode: int | None) -> None:
        nonlocal calls
        calls += 1
        if calls == 2:
            raise OSError("injected write failure")
        real_atomic_write(path, content, mode)

    monkeypatch.setattr(sync_module, "_atomic_write", fail_once)

    with pytest.raises(SyncError, match="rolled back.*injected write failure"):
        synchronize(root, apply=True)

    for path, content in originals.items():
        assert path.read_bytes() == content
    assert not (root / "skills" / "beta-skill").exists()
    assert not (beta / "skills" / "alpha-skill").exists()


def test_apply_noop_does_not_create_empty_backup(tmp_path: Path):
    root = tmp_path / "home"
    _write_profile(root, mcp={}, env="OPENAI_API_KEY=one\n", skill="alpha-skill")

    report = synchronize(root, apply=True)

    assert report.backup_dir is None
    assert not (root / "backups").exists()


def _link_skill_tree(target: Path, link: Path) -> None:
    """Point *link* at the canonical tree *target*, the way this host links.

    Windows gets a junction (what the local profiles use, and what
    ``Path.rglob`` follows); POSIX gets a symlink. Skip where the host refuses.
    """
    if os.name == "nt":  # pragma: no cover - platform branch
        import _winapi

        try:
            _winapi.CreateJunction(str(target), str(link))
            return
        except (AttributeError, ImportError, OSError):
            pass
    try:
        link.symlink_to(target, target_is_directory=True)
    except (OSError, NotImplementedError):
        pytest.skip("host cannot create directory links")


def test_sync_replaces_linked_skill_without_rmtree_failure(tmp_path: Path):
    """A skill reached through a junction/symlink must sync like any other tree.

    ``shutil.rmtree`` refuses a reparse point on Windows ("Cannot call rmtree on
    a symbolic link"), so the post-apply cleanup aborted *after* every profile's
    link had been renamed aside: the run never reported success and left
    ``.sync-old-*`` links behind. ``Path.rglob`` also skips directory symlinks,
    which made a linked skill invisible to conflict detection and then failed
    the post-write digest check. Profiles legitimately link canonical trees.
    """
    root = tmp_path / "home"
    _write_profile(root, mcp={}, env="OPENAI_API_KEY=one\n", skill="shared-skill")
    (root / "skills" / "shared-skill" / "implementation.py").write_text(
        "CANONICAL = True\n", encoding="utf-8"
    )

    beta = root / "profiles" / "beta"
    _write_profile(
        beta, mcp={}, env="OPENAI_API_KEY=one\n", skill="shared-skill", token=True
    )
    canonical = tmp_path / "canonical" / "beta" / "shared-skill"
    canonical.mkdir(parents=True)
    (canonical / "SKILL.md").write_text("---\nname: shared-skill\n---\n", encoding="utf-8")
    (canonical / "obsolete.py").write_text("OBSOLETE = True\n", encoding="utf-8")
    (canonical / "account_token.json").write_text("secret", encoding="utf-8")

    beta_skill = beta / "skills" / "shared-skill"
    shutil.rmtree(beta_skill)
    _link_skill_tree(canonical, beta_skill)
    assert is_reparse_point(beta_skill), "test must exercise the link-removal path"

    report = synchronize(root, apply=True, resolve_skill_conflicts_from_default=True)

    assert report.replaced_skills == {"beta": ["shared-skill"]}
    assert not is_reparse_point(beta_skill)
    assert (beta_skill / "implementation.py").read_text(encoding="utf-8") == "CANONICAL = True\n"
    assert not (beta_skill / "obsolete.py").exists()
    assert (beta_skill / "account_token.json").read_text(encoding="utf-8") == "secret"
    assert (canonical / "obsolete.py").is_file()
    assert list((beta / "skills").glob(".shared-skill.sync-old-*")) == []
