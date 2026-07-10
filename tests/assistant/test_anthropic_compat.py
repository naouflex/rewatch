"""Tests for Anthropic schema and message compatibility helpers."""

import json

from rewatch.assistant.anthropic_compat import normalize_anthropic_messages, sanitize_json_schema
from rewatch.assistant.llm_client import openai_messages_to_anthropic, openai_tools_to_anthropic


def test_sanitize_json_schema_strips_defaults_and_unsupported_keys():
    schema = {
        "type": "object",
        "properties": {
            "page_size": {"type": "integer", "default": 10, "minimum": 1, "maximum": 100},
            "query": {"type": "string", "minLength": 1},
        },
        "additionalProperties": False,
        "required": ["query"],
    }
    cleaned = sanitize_json_schema(schema)
    assert "default" not in cleaned["properties"]["page_size"]
    assert "minimum" not in cleaned["properties"]["page_size"]
    assert "additionalProperties" not in cleaned
    assert cleaned["properties"]["page_size"]["type"] == "integer"


def test_openai_tools_to_anthropic_sanitizes_schema():
    tools = openai_tools_to_anthropic(
        [
            {
                "type": "function",
                "function": {
                    "name": "search_queries",
                    "description": "Search",
                    "parameters": {
                        "type": "object",
                        "properties": {"page_size": {"type": "integer", "default": 10}},
                        "required": ["q"],
                    },
                },
            }
        ]
    )
    assert "default" not in json.dumps(tools[0]["input_schema"])


def test_normalize_anthropic_messages_merges_consecutive_users():
    merged = normalize_anthropic_messages(
        [
            {"role": "user", "content": "First"},
            {"role": "user", "content": "Second"},
        ]
    )
    assert merged == [{"role": "user", "content": "First\n\nSecond"}]


def test_openai_messages_to_anthropic_keeps_tool_only_assistant_turn():
    converted = openai_messages_to_anthropic(
        [
            {"role": "user", "content": "Run it"},
            {
                "role": "assistant",
                "content": "",
                "tool_calls": [
                    {
                        "id": "toolu_abc",
                        "type": "function",
                        "function": {"name": "run_query", "arguments": json.dumps({"query_id": 3})},
                    }
                ],
            },
            {"role": "tool", "tool_call_id": "toolu_abc", "content": '{"rows": []}'},
        ]
    )
    assert converted[1]["role"] == "assistant"
    assert converted[1]["content"][0]["type"] == "tool_use"
    assert converted[2]["role"] == "user"
    assert converted[2]["content"][0]["type"] == "tool_result"
