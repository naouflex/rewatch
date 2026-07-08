"""Tests for assistant session context formatting."""

from rewatch.assistant.session_context import (
    extract_resource_ids_from_payload,
    format_session_context,
)


def test_format_session_context_empty():
    assert format_session_context([]) is None
    assert format_session_context([{"role": "user", "content": "hi"}]) is None


def test_format_session_context_includes_tool_summaries():
    messages = [
        {"role": "user", "content": "Create a dashboard"},
        {
            "role": "assistant",
            "content": "Done.",
            "decision_graph": {
                "nodes": [
                    {
                        "type": "tool",
                        "tool": "create_dashboard",
                        "arguments": {"name": "Ops"},
                        "result_summary": "Dashboard #42",
                        "resource_ids": {"dashboard_id": 42},
                    }
                ]
            },
        },
    ]
    context = format_session_context(messages)
    assert context is not None
    assert "create_dashboard" in context
    assert "Dashboard #42" in context
    assert "dashboard_id: 42" in context


def test_extract_resource_ids_from_payload():
    payload = {
        "query_id": 7,
        "dashboard": {"id": 99, "name": "Test"},
    }
    ids = extract_resource_ids_from_payload(payload)
    assert ids["query_id"] == 7
    assert ids["dashboard_id"] == 99
