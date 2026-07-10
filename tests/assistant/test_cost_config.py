"""Tests for provider-specific assistant cost controls."""

import json

from rewatch.assistant.llm_client import compact_openai_tools, openai_tools_to_anthropic
from rewatch.assistant.llm_config import (
    assistant_compact_tools_enabled,
    assistant_include_skill_guides,
    assistant_max_tokens,
    assistant_max_tool_result_chars,
    assistant_max_tool_rounds,
    assistant_model,
    assistant_prompt_caching_enabled,
    assistant_skill_guides_max_chars,
)


class TestAnthropicCostDefaults:
    def test_anthropic_uses_lower_limits(self, monkeypatch):
        monkeypatch.setattr("rewatch.settings.ASSISTANT_PROVIDER", "anthropic")
        monkeypatch.setattr("rewatch.settings.ANTHROPIC_API_KEY", "ant-test")
        monkeypatch.setattr("rewatch.settings.OPENAI_API_KEY", "")
        monkeypatch.setattr("rewatch.settings.ASSISTANT_ANTHROPIC_MODEL", "claude-sonnet-4-6")
        monkeypatch.setattr("rewatch.settings.ASSISTANT_ANTHROPIC_MAX_TOKENS", 8192)
        monkeypatch.setattr("rewatch.settings.ASSISTANT_ANTHROPIC_MAX_TOOL_ROUNDS", 20)
        monkeypatch.setattr("rewatch.settings.ASSISTANT_ANTHROPIC_MAX_TOOL_RESULT_CHARS", 16000)
        monkeypatch.setattr("rewatch.settings.ASSISTANT_ANTHROPIC_INCLUDE_SKILL_GUIDES", False)
        monkeypatch.setattr("rewatch.settings.ASSISTANT_ANTHROPIC_SKILL_GUIDES_MAX_CHARS", 8000)
        monkeypatch.setattr("rewatch.settings.ASSISTANT_ANTHROPIC_PROMPT_CACHING", True)
        monkeypatch.setattr("rewatch.settings.ASSISTANT_ANTHROPIC_COMPACT_TOOLS", True)

        assert assistant_model() == "claude-sonnet-4-6"
        assert assistant_max_tokens() == 8192
        assert assistant_max_tool_rounds() == 20
        assert assistant_max_tool_result_chars() == 16000
        assert assistant_include_skill_guides() is False
        assert assistant_skill_guides_max_chars() == 8000
        assert assistant_prompt_caching_enabled() is True
        assert assistant_compact_tools_enabled() is True

    def test_openai_keeps_generous_limits(self, monkeypatch):
        monkeypatch.setattr("rewatch.settings.ASSISTANT_PROVIDER", "openai")
        monkeypatch.setattr("rewatch.settings.OPENAI_API_KEY", "sk-test")
        monkeypatch.setattr("rewatch.settings.ASSISTANT_MAX_TOKENS", 16384)
        monkeypatch.setattr("rewatch.settings.ASSISTANT_MAX_TOOL_ROUNDS", 40)
        monkeypatch.setattr("rewatch.settings.ASSISTANT_MAX_TOOL_RESULT_CHARS", 48000)
        monkeypatch.setattr("rewatch.settings.ASSISTANT_INCLUDE_SKILL_GUIDES", True)

        assert assistant_max_tokens() == 16384
        assert assistant_max_tool_rounds() == 40
        assert assistant_max_tool_result_chars() == 48000
        assert assistant_include_skill_guides() is True
        assert assistant_compact_tools_enabled() is False
        assert assistant_prompt_caching_enabled() is False


def test_compact_openai_tools_truncates_descriptions(monkeypatch):
    monkeypatch.setattr("rewatch.settings.ASSISTANT_PROVIDER", "anthropic")
    monkeypatch.setattr("rewatch.settings.ANTHROPIC_API_KEY", "ant-test")
    monkeypatch.setattr("rewatch.settings.ASSISTANT_ANTHROPIC_COMPACT_TOOLS", True)
    monkeypatch.setattr("rewatch.settings.ASSISTANT_ANTHROPIC_TOOL_DESCRIPTION_MAX_CHARS", 40)

    tools = [
        {
            "type": "function",
            "function": {
                "name": "demo_tool",
                "description": "A" * 120,
                "parameters": {"type": "object", "properties": {}},
            },
        }
    ]
    compacted = compact_openai_tools(tools)
    assert len(compacted[0]["function"]["description"]) <= 40
    assert compacted[0]["function"]["description"].endswith("…")

    converted = openai_tools_to_anthropic(compacted)
    assert converted[0]["description"].endswith("…")
