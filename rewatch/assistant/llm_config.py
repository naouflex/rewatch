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


def _use_anthropic_limits() -> bool:
    return effective_assistant_provider() == "anthropic"


def assistant_enabled() -> bool:
    return bool(settings.ASSISTANT_ENABLED and assistant_api_key_configured())


def assistant_model() -> str:
    if _use_anthropic_limits():
        return settings.ASSISTANT_ANTHROPIC_MODEL
    return settings.ASSISTANT_OPENAI_MODEL


def assistant_max_tokens() -> int:
    if _use_anthropic_limits():
        return settings.ASSISTANT_ANTHROPIC_MAX_TOKENS
    return settings.ASSISTANT_MAX_TOKENS


def assistant_max_tool_rounds() -> int:
    if _use_anthropic_limits():
        return settings.ASSISTANT_ANTHROPIC_MAX_TOOL_ROUNDS
    return settings.ASSISTANT_MAX_TOOL_ROUNDS


def assistant_max_tool_result_chars() -> int:
    if _use_anthropic_limits():
        return settings.ASSISTANT_ANTHROPIC_MAX_TOOL_RESULT_CHARS
    return settings.ASSISTANT_MAX_TOOL_RESULT_CHARS


def assistant_include_skill_guides() -> bool:
    if _use_anthropic_limits():
        return settings.ASSISTANT_ANTHROPIC_INCLUDE_SKILL_GUIDES
    return settings.ASSISTANT_INCLUDE_SKILL_GUIDES


def assistant_skill_guides_max_chars() -> int:
    if _use_anthropic_limits():
        return settings.ASSISTANT_ANTHROPIC_SKILL_GUIDES_MAX_CHARS
    return settings.ASSISTANT_SKILL_GUIDES_MAX_CHARS


def assistant_max_llm_chars() -> int:
    if _use_anthropic_limits():
        return settings.ASSISTANT_ANTHROPIC_MAX_LLM_CHARS
    return settings.ASSISTANT_MAX_LLM_CHARS


def assistant_max_llm_messages() -> int:
    if _use_anthropic_limits():
        return settings.ASSISTANT_ANTHROPIC_MAX_LLM_MESSAGES
    return settings.ASSISTANT_MAX_LLM_MESSAGES


def assistant_prompt_caching_enabled() -> bool:
    return _use_anthropic_limits() and settings.ASSISTANT_ANTHROPIC_PROMPT_CACHING


def assistant_compact_tools_enabled() -> bool:
    return _use_anthropic_limits() and settings.ASSISTANT_ANTHROPIC_COMPACT_TOOLS


def assistant_tool_description_max_chars() -> int:
    if _use_anthropic_limits():
        return settings.ASSISTANT_ANTHROPIC_TOOL_DESCRIPTION_MAX_CHARS
    return 0


def assistant_provider_label() -> str:
    return "Anthropic" if effective_assistant_provider() == "anthropic" else "OpenAI"


def assistant_api_key_env_var() -> str:
    return "REWATCH_ANTHROPIC_API_KEY" if effective_assistant_provider() == "anthropic" else "REWATCH_OPENAI_API_KEY"
