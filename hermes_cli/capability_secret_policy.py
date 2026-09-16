"""Explicit policy for environment-backed Hermes capabilities.

Only keys classified as ``shared_static`` or ``shared_endpoint`` may be
materialized across profiles.  OAuth refresh material, device sessions, and
gateway-service secrets stay local to their owning profile/service.  Unknown
keys are intentionally ambiguous so the synchronizer fails before mutation
instead of guessing from a suffix such as ``_TOKEN``.
"""

from __future__ import annotations

import re
from dataclasses import dataclass


@dataclass(frozen=True)
class EnvKeyPolicy:
    scope: str
    secret: bool
    issuer: str | None = None

    @property
    def shared(self) -> bool:
        return self.scope in {"shared_static", "shared_endpoint"}

    @property
    def ambiguous(self) -> bool:
        return self.scope in {"ambiguous", "ambiguous_secret"}


_POLICIES: dict[str, EnvKeyPolicy] = {
    # Shared static account credentials.
    "AI_GATEWAY_API_KEY": EnvKeyPolicy("shared_static", True, "Nous AI Gateway"),
    "ANTHROPIC_API_KEY": EnvKeyPolicy("shared_static", True, "Anthropic"),
    "BRAVE_SEARCH_API_KEY": EnvKeyPolicy("shared_static", True, "Brave Search"),
    "DEEPSEEK_API_KEY": EnvKeyPolicy("shared_static", True, "DeepSeek"),
    "ELEVENLABS_API_KEY": EnvKeyPolicy("shared_static", True, "ElevenLabs"),
    "FIRECRAWL_API_KEY": EnvKeyPolicy("shared_static", True, "Firecrawl"),
    "GITHUB_TOKEN": EnvKeyPolicy("shared_static", True, "GitHub"),
    "GOOGLE_API_KEY": EnvKeyPolicy("shared_static", True, "Google Cloud"),
    "HASS_TOKEN": EnvKeyPolicy("shared_static", True, "Home Assistant"),
    "HF_TOKEN": EnvKeyPolicy("shared_static", True, "Hugging Face"),
    "LM_API_KEY": EnvKeyPolicy("shared_static", True, "LM Studio"),
    "OLLAMA_API_KEY": EnvKeyPolicy("shared_static", True, "Ollama Cloud"),
    "OPENAI_API_KEY": EnvKeyPolicy("shared_static", True, "OpenAI"),
    "OPENROUTER_API_KEY": EnvKeyPolicy("shared_static", True, "OpenRouter"),
    "XAI_API_KEY": EnvKeyPolicy("shared_static", True, "xAI"),
    # Shared endpoints are capability wiring, not credentials.
    "HASS_URL": EnvKeyPolicy("shared_endpoint", False, "Home Assistant"),
    "LM_BASE_URL": EnvKeyPolicy("shared_endpoint", False, "LM Studio"),
    "SEARXNG_URL": EnvKeyPolicy("shared_endpoint", False, "SearXNG"),
    # Gateway/service-local material must not be propagated to named profiles.
    "EMAIL_HOME_ADDRESS": EnvKeyPolicy("service_local", False, "Hermes Email Gateway"),
    "TELEGRAM_ALLOWED_USERS": EnvKeyPolicy("service_local", False, "Telegram"),
    "TELEGRAM_BOT_TOKEN": EnvKeyPolicy("service_local", True, "Telegram"),
    "WHATSAPP_ALLOWED_USERS": EnvKeyPolicy("service_local", False, "WhatsApp"),
    "WHATSAPP_DM_POLICY": EnvKeyPolicy("service_local", False, "WhatsApp"),
    "WHATSAPP_ENABLED": EnvKeyPolicy("service_local", False, "WhatsApp"),
    "WHATSAPP_MODE": EnvKeyPolicy("service_local", False, "WhatsApp"),
    # Known host-local behavior settings are preserved in place but unmanaged.
    "AGENT_BROWSER_EXECUTABLE_PATH": EnvKeyPolicy("local_setting", False),
    "BROWSER_INACTIVITY_TIMEOUT": EnvKeyPolicy("local_setting", False),
    "BROWSER_SESSION_TIMEOUT": EnvKeyPolicy("local_setting", False),
    "BROWSERBASE_ADVANCED_STEALTH": EnvKeyPolicy("local_setting", False),
    "BROWSERBASE_PROXIES": EnvKeyPolicy("local_setting", False),
    "IMAGE_TOOLS_DEBUG": EnvKeyPolicy("local_setting", False),
    "MOA_TOOLS_DEBUG": EnvKeyPolicy("local_setting", False),
    "TERMINAL_ENV": EnvKeyPolicy("local_setting", False),
    "TERMINAL_LIFETIME_SECONDS": EnvKeyPolicy("local_setting", False),
    "TERMINAL_MODAL_IMAGE": EnvKeyPolicy("local_setting", False),
    "TERMINAL_TIMEOUT": EnvKeyPolicy("local_setting", False),
    "VISION_TOOLS_DEBUG": EnvKeyPolicy("local_setting", False),
    "WEB_TOOLS_DEBUG": EnvKeyPolicy("local_setting", False),
}

_ROTATING_OAUTH_RE = re.compile(
    r"(?:^|_)(?:OAUTH|ACCESS_TOKEN|REFRESH_TOKEN|ID_TOKEN)(?:_|$)", re.IGNORECASE
)
_DEVICE_SESSION_RE = re.compile(
    r"(?:^|_)(?:DEVICE|SESSION|PAIRING|LINKED_DEVICE)(?:_|$)", re.IGNORECASE
)
_SECRET_SHAPE_RE = re.compile(
    r"(?:^|_)(?:API_KEY|TOKEN|SECRET|PASSWORD|PRIVATE_KEY|CREDENTIAL)(?:_|$)",
    re.IGNORECASE,
)


def classify_env_key(key: str) -> EnvKeyPolicy:
    """Classify one env key without inspecting its value."""
    normalized = str(key).strip().upper()
    known = _POLICIES.get(normalized)
    if known is not None:
        return known
    if _ROTATING_OAUTH_RE.search(normalized):
        return EnvKeyPolicy("rotating_oauth", True)
    if _DEVICE_SESSION_RE.search(normalized):
        return EnvKeyPolicy("device_session", True)
    if _SECRET_SHAPE_RE.search(normalized):
        return EnvKeyPolicy("ambiguous_secret", True)
    return EnvKeyPolicy("ambiguous", False)


def known_env_keys() -> frozenset[str]:
    return frozenset(_POLICIES)

