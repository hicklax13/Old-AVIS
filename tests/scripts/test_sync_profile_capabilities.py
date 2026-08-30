from pathlib import Path

import pytest
import yaml

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


def test_sync_unions_capabilities_without_copying_refreshable_skill_tokens(tmp_path: Path):
    root = tmp_path / "home"
    _write_profile(
        root,
        mcp={"alpha": {"url": "https://alpha.example/mcp", "auth": "oauth"}},
        env="ALPHA_KEY=one\n",
        skill="alpha-skill",
        token=True,
    )
    beta = root / "profiles" / "beta"
    _write_profile(
        beta,
        mcp={"beta": {"url": "https://beta.example/mcp", "enabled": False}},
        env="BETA_KEY=two\n",
        skill="beta-skill",
        token=True,
    )

    dry_run = synchronize(root, apply=False)

    assert dry_run.changed_configs == ["beta", "default"]
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
        assert "ALPHA_KEY=one" in env_text
        assert "BETA_KEY=two" in env_text
        assert (profile / "skills" / "alpha-skill" / "SKILL.md").is_file()
        assert (profile / "skills" / "beta-skill" / "SKILL.md").is_file()

    assert not (root / "skills" / "beta-skill" / "account_token.json").exists()
    assert not (beta / "skills" / "alpha-skill" / "account_token.json").exists()


def test_sync_refuses_conflicting_static_account_keys_before_writes(tmp_path: Path):
    root = tmp_path / "home"
    _write_profile(
        root,
        mcp={},
        env="SHARED_KEY=one\n",
        skill="alpha-skill",
    )
    beta = root / "profiles" / "beta"
    _write_profile(
        beta,
        mcp={},
        env="SHARED_KEY=two\n",
        skill="beta-skill",
    )
    before = (root / "config.yaml").read_bytes()

    with pytest.raises(SyncError, match="SHARED_KEY"):
        synchronize(root, apply=True)

    assert (root / "config.yaml").read_bytes() == before
    assert not (root / "backups" / "profile-capability-sync").exists()


def test_default_profile_definition_wins_mcp_conflicts(tmp_path: Path):
    root = tmp_path / "home"
    _write_profile(
        root,
        mcp={"shared": {"url": "https://default.example/mcp"}},
        env="KEY=one\n",
        skill="alpha-skill",
    )
    beta = root / "profiles" / "beta"
    _write_profile(
        beta,
        mcp={"shared": {"url": "https://beta.example/mcp"}},
        env="KEY=one\n",
        skill="beta-skill",
    )

    synchronize(root, apply=True)

    for profile in (root, beta):
        cfg = yaml.safe_load((profile / "config.yaml").read_text(encoding="utf-8"))
        assert cfg["mcp_servers"]["shared"]["url"] == "https://default.example/mcp"
