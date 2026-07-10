"""Tests for assistant LLM provider configuration and message conversion."""

import json

from rewatch.assistant.llm_client import openai_messages_to_anthropic, openai_tools_to_anthropic, split_system_messages
from rewatch.assistant.llm_config import (
    assistant_api_key_env_var,
    assistant_enabled,
    assistant_model,
    assistant_provider,
)


class TestLLMConfig:
    def test_defaults_to_openai_without_anthropic_key(self, monkeypatch):
        monkeypatch.setattr("rewatch.settings.ASSISTANT_PROVIDER", "openai")
        monkeypatch.setattr("rewatch.settings.ANTHROPIC_API_KEY", "")
        monkeypatch.setattr("rewatch.settings.OPENAI_API_KEY", "sk-test")
        monkeypatch.setattr("rewatch.settings.ASSISTANT_ENABLED", True)
        monkeypatch.setattr("rewatch.settings.ASSISTANT_OPENAI_MODEL", "gpt-test")
        assert assistant_provider() == "openai"
        assert assistant_model() == "gpt-test"
        assert assistant_enabled() is True
        assert assistant_api_key_env_var() == "REWATCH_OPENAI_API_KEY"

    def test_anthropic_provider_and_model(self, monkeypatch):
        monkeypatch.setattr("rewatch.settings.ASSISTANT_PROVIDER", "anthropic")
        monkeypatch.setattr("rewatch.settings.ANTHROPIC_API_KEY", "ant-test")
        monkeypatch.setattr("rewatch.settings.ASSISTANT_ENABLED", True)
        monkeypatch.setattr("rewatch.settings.ASSISTANT_ANTHROPIC_MODEL", "claude-opus-4-6")
        assert assistant_provider() == "anthropic"
        assert assistant_model() == "claude-opus-4-6"
        assert assistant_enabled() is True
        assert assistant_api_key_env_var() == "REWATCH_ANTHROPIC_API_KEY"

    def test_anthropic_provider_falls_back_to_openai_without_key(self, monkeypatch):
        from rewatch.assistant.llm_config import effective_assistant_provider

        monkeypatch.setattr("rewatch.settings.ASSISTANT_PROVIDER", "anthropic")
        monkeypatch.setattr("rewatch.settings.ANTHROPIC_API_KEY", "")
        monkeypatch.setattr("rewatch.settings.OPENAI_API_KEY", "sk-test")
        monkeypatch.setattr("rewatch.settings.ASSISTANT_ENABLED", True)
        monkeypatch.setattr("rewatch.settings.ASSISTANT_OPENAI_MODEL", "gpt-test")
        assert assistant_enabled() is True
        assert effective_assistant_provider() == "openai"
        assert assistant_model() == "gpt-test"


class TestAnthropicMessageConversion:
    def test_split_system_messages(self):
        system, other = split_system_messages(
            [
                {"role": "system", "content": "You are helpful."},
                {"role": "user", "content": "Hi"},
            ]
        )
        assert system == "You are helpful."
        assert other == [{"role": "user", "content": "Hi"}]

    def test_openai_tools_to_anthropic(self):
        tools = [
            {
                "type": "function",
                "function": {
                    "name": "run_query",
                    "description": "Execute a query",
                    "parameters": {"type": "object", "properties": {"query_id": {"type": "integer"}}},
                },
            }
        ]
        converted = openai_tools_to_anthropic(tools)
        assert converted[0]["name"] == "run_query"
        assert converted[0]["input_schema"]["properties"]["query_id"]["type"] == "integer"

    def test_openai_messages_to_anthropic_tool_roundtrip(self):
        messages = [
            {"role": "user", "content": "Run it"},
            {
                "role": "assistant",
                "content": "Checking…",
                "tool_calls": [
                    {
                        "id": "toolu_123",
                        "type": "function",
                        "function": {"name": "run_query", "arguments": json.dumps({"query_id": 7})},
                    }
                ],
            },
            {"role": "tool", "tool_call_id": "toolu_123", "content": '{"rows": []}'},
            {"role": "assistant", "content": "Done."},
        ]

        converted = openai_messages_to_anthropic(messages)

        assert converted[0] == {"role": "user", "content": "Run it"}
        assert converted[1]["role"] == "assistant"
        assert converted[1]["content"][0] == {"type": "text", "text": "Checking…"}
        assert converted[1]["content"][1]["type"] == "tool_use"
        assert converted[1]["content"][1]["name"] == "run_query"
        assert converted[1]["content"][1]["input"] == {"query_id": 7}
        assert converted[2]["role"] == "user"
        assert converted[2]["content"][0]["type"] == "tool_result"
        assert converted[2]["content"][0]["tool_use_id"] == "toolu_123"
        assert converted[3] == {"role": "assistant", "content": "Done."}
