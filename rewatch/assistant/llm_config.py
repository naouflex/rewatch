"""Assistant LLM provider configuration."""

from __future__ import annotations

from rewatch import settings


def assistant_provider() -> str:
    return settings.ASSISTANT_PROVIDER


def assistant_api_key_configured() -> bool:
    if assistant_provider() == "anthropic":
        if settings.ANTHROPIC_API_KEY:
            return True
        # Fall back when provider is misconfigured but OpenAI is available.
        return bool(settings.OPENAI_API_KEY)
    return bool(settings.OPENAI_API_KEY)


def effective_assistant_provider() -> str:
    """Provider that will actually be used for API calls."""
    if assistant_provider() == "anthropic" and settings.ANTHROPIC_API_KEY:
        return "anthropic"
    if settings.OPENAI_API_KEY:
        return "openai"
    if settings.ANTHROPIC_API_KEY:
        return "anthropic"
    return assistant_provider()


def assistant_enabled() -> bool:
    return bool(settings.ASSISTANT_ENABLED and assistant_api_key_configured())


def assistant_model() -> str:
    if effective_assistant_provider() == "anthropic":
        return settings.ASSISTANT_ANTHROPIC_MODEL
    return settings.ASSISTANT_OPENAI_MODEL


def assistant_provider_label() -> str:
    return "Anthropic" if effective_assistant_provider() == "anthropic" else "OpenAI"


def assistant_api_key_env_var() -> str:
    return "REDASH_ANTHROPIC_API_KEY" if effective_assistant_provider() == "anthropic" else "REDASH_OPENAI_API_KEY"
