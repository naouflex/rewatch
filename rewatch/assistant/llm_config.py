"""Assistant LLM provider configuration."""

from __future__ import annotations

from rewatch import settings


def assistant_provider() -> str:
    return settings.ASSISTANT_PROVIDER


def assistant_api_key_configured() -> bool:
    if assistant_provider() == "anthropic":
        return bool(settings.ANTHROPIC_API_KEY)
    return bool(settings.OPENAI_API_KEY)


def assistant_enabled() -> bool:
    return bool(settings.ASSISTANT_ENABLED and assistant_api_key_configured())


def assistant_model() -> str:
    if assistant_provider() == "anthropic":
        return settings.ASSISTANT_ANTHROPIC_MODEL
    return settings.ASSISTANT_OPENAI_MODEL


def assistant_provider_label() -> str:
    return "Anthropic" if assistant_provider() == "anthropic" else "OpenAI"


def assistant_api_key_env_var() -> str:
    return "REDASH_ANTHROPIC_API_KEY" if assistant_provider() == "anthropic" else "REDASH_OPENAI_API_KEY"
