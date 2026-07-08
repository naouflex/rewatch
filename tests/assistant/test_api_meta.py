"""Tests for OpenAPI meta-tools."""

import json

from rewatch.assistant import api_meta


def test_list_endpoints_filters_tag():
    def fake_request(method, path, **kwargs):
        assert method == "GET"
        assert path == "/api/spec"
        return {
            "paths": {
                "/api/queries": {
                    "get": {"tags": ["Queries"], "summary": "List queries"},
                },
                "/api/dashboards": {
                    "get": {"tags": ["Dashboards"], "summary": "List dashboards"},
                },
            },
            "tags": [{"name": "Queries"}, {"name": "Dashboards"}],
        }

    api_meta.clear_spec_cache()
    text = api_meta.list_endpoints(fake_request, tag="Queries")
    assert "/api/queries" in text
    assert "/api/dashboards" not in text


def test_describe_endpoint_returns_operation():
    spec = {
        "paths": {
            "/api/queries/{query_id}": {
                "get": {"summary": "Get query", "parameters": [{"name": "query_id"}]},
            }
        }
    }

    def fake_request(method, path, **kwargs):
        return spec

    api_meta.clear_spec_cache()
    op = api_meta.describe_endpoint(fake_request, method="GET", path="/api/queries/{query_id}")
    assert op["summary"] == "Get query"


def test_call_api_rejects_template_path():
    def fake_request(method, path, **kwargs):
        return {"ok": True}

    try:
        api_meta.call_api(fake_request, method="GET", path="/api/queries/{query_id}")
        assert False, "expected RuntimeError"
    except RuntimeError as exc:
        assert "placeholder" in str(exc).lower()


def test_prepare_messages_for_llm_injects_context():
    from rewatch.assistant.storage import prepare_messages_for_llm

    messages = [
        {"role": "user", "content": "Build dashboard"},
        {
            "role": "assistant",
            "content": "Created dashboard 5.",
            "decision_graph": {
                "nodes": [
                    {
                        "type": "tool",
                        "tool": "create_dashboard",
                        "arguments": {"name": "Ops"},
                        "result_summary": "Dashboard #5",
                        "resource_ids": {"dashboard_id": 5},
                    }
                ]
            },
        },
        {"role": "user", "content": "Add an alert"},
    ]
    llm_messages, session_context = prepare_messages_for_llm(messages)
    assert llm_messages[-1]["content"] == "Add an alert"
    assert session_context is not None
    assert "dashboard_id: 5" in session_context
