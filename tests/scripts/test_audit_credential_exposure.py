from __future__ import annotations

import json
import zipfile
from pathlib import Path

from hermes_cli.capability_secret_policy import classify_env_key
from scripts.audit_credential_exposure import build_inventory


def test_current_environment_keys_are_all_explicitly_classified() -> None:
    expected = {
        "AGENT_BROWSER_EXECUTABLE_PATH",
        "AI_GATEWAY_API_KEY",
        "ANTHROPIC_API_KEY",
        "BRAVE_SEARCH_API_KEY",
        "BROWSER_INACTIVITY_TIMEOUT",
        "BROWSER_SESSION_TIMEOUT",
        "BROWSERBASE_ADVANCED_STEALTH",
        "BROWSERBASE_PROXIES",
        "DEEPSEEK_API_KEY",
        "ELEVENLABS_API_KEY",
        "EMAIL_HOME_ADDRESS",
        "FIRECRAWL_API_KEY",
        "GITHUB_TOKEN",
        "GOOGLE_API_KEY",
        "HASS_TOKEN",
        "HASS_URL",
        "HF_TOKEN",
        "IMAGE_TOOLS_DEBUG",
        "LM_API_KEY",
        "LM_BASE_URL",
        "MOA_TOOLS_DEBUG",
        "OPENAI_API_KEY",
        "OPENROUTER_API_KEY",
        "SEARXNG_URL",
        "TELEGRAM_ALLOWED_USERS",
        "TELEGRAM_BOT_TOKEN",
        "TERMINAL_ENV",
        "TERMINAL_LIFETIME_SECONDS",
        "TERMINAL_MODAL_IMAGE",
        "TERMINAL_TIMEOUT",
        "VISION_TOOLS_DEBUG",
        "WEB_TOOLS_DEBUG",
        "WHATSAPP_ALLOWED_USERS",
        "WHATSAPP_DM_POLICY",
        "WHATSAPP_ENABLED",
        "WHATSAPP_MODE",
        "XAI_API_KEY",
    }

    assert all(not classify_env_key(key).ambiguous for key in expected)


def test_unknown_secret_is_ambiguous_and_never_shared() -> None:
    policy = classify_env_key("NEW_VENDOR_API_KEY")

    assert policy.scope == "ambiguous_secret"
    assert policy.secret is True
    assert policy.shared is False


def test_inventory_never_serializes_secret_values(tmp_path: Path) -> None:
    home = tmp_path / "home"
    backups = home / "backups"
    backups.mkdir(parents=True)
    secret_value = "secret-value-that-must-never-appear"
    (home / ".env").write_text(f"OPENAI_API_KEY={secret_value}\n", encoding="utf-8")
    tokens = home / "mcp-tokens"
    tokens.mkdir()
    (tokens / "stripe.client.json").write_text(secret_value, encoding="utf-8")
    (tokens / "stripe.json").write_text(secret_value, encoding="utf-8")
    (home / "auth.json").write_text(
        json.dumps({"providers": {"openai-codex": {"token": secret_value}}}),
        encoding="utf-8",
    )
    google_profile = home / "profiles" / "google-personal"
    google_profile.mkdir(parents=True)
    for filename in (
        "google_client_secret.json",
        "google_token.json",
        "youtube_client_secret.json",
        "youtube_token.json",
    ):
        (google_profile / filename).write_text(secret_value, encoding="utf-8")
    archive = backups / "pre-update.zip"
    with zipfile.ZipFile(archive, "w") as zipped:
        zipped.writestr("profile/.env", f"GITHUB_TOKEN={secret_value}\n")
        zipped.writestr("profile/mcp-tokens/vercel.json", secret_value)
        zipped.writestr("services/n8n/data/config", secret_value)
        zipped.writestr("profiles/google-school/google_token.json", secret_value)
        zipped.writestr("profiles/google-school/youtube_token.json", secret_value)

    report = build_inventory(home)
    serialized = json.dumps(report)

    assert secret_value not in serialized
    issuers = {item["issuer"] for item in report["affected_issuers"]}
    assert {
        "OpenAI",
        "GitHub",
        "MCP OAuth: vercel",
        "MCP OAuth: stripe",
        "Hermes provider auth: openai-codex",
        "Google Workspace OAuth",
        "YouTube OAuth",
        "n8n",
    } <= issuers
    assert report["policy"]["contains_secret_values"] is False
    archive_record = next(item for item in report["archives"] if item["archive"] == archive.name)
    assert archive_record["env_keys"] == ["GITHUB_TOKEN"]
