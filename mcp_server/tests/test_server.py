"""Unit tests for the MCP server tools (no live API; _request is monkeypatched).

Run from mcp_server/: uv run --with pytest pytest tests/
"""

import json

import pytest

from rewatch_mcp import server


@pytest.fixture(autouse=True)
def writable_mode(monkeypatch):
    """Pin read-only off so a REWATCH_MCP_READ_ONLY in .env cannot break tests."""
    monkeypatch.setattr(server, "READ_ONLY", False)


@pytest.fixture
def fake_request(monkeypatch):
    calls = []

    def _fake(method, path, *, params=None, body=None):
        calls.append((method, path, body))
        if method == "GET" and path == "/api/dashboards/7":
            return {
                "id": 7,
                "slug": "demo",
                "name": "Demo",
                "is_draft": True,
                "widgets": [
                    {
                        "id": 10,
                        "options": {"position": {"col": 0, "row": 0, "sizeX": 6, "sizeY": 3}},
                        "visualization": {"id": 5, "type": "CHART", "name": "TVL"},
                    }
                ],
            }
        if method == "GET" and path == "/api/visualizations/5":
            return {"id": 5, "type": "COUNTER", "name": "KPI"}
        if method == "POST" and path == "/api/widgets":
            return {"id": 99, **(body or {})}
        raise AssertionError(f"Unexpected request: {method} {path}")

    monkeypatch.setattr(server, "_request", _fake)
    return calls


def test_get_dashboard_returns_layout_summary(fake_request):
    payload = json.loads(server.get_dashboard(7))
    assert payload["layout_summary"]["widget_count"] == 1
    assert payload["layout_summary"]["widgets"][0]["widget_id"] == 10


def test_add_widget_auto_places_with_type_aware_size(fake_request):
    payload = json.loads(server.add_widget_to_dashboard(dashboard_id=7, visualization_id=5))
    position = payload["options"]["position"]
    # Existing widget occupies rows 0-2; a counter goes below at 3x3.
    assert {k: position[k] for k in ("col", "row", "sizeX", "sizeY")} == {
        "col": 0,
        "row": 3,
        "sizeX": 3,
        "sizeY": 3,
    }


def test_composite_dashboard_tools_are_registered():
    for tool_name in (
        "build_dashboard_from_spec",
        "refresh_queries_and_wait",
        "create_multi_visualization_query",
    ):
        assert hasattr(server, tool_name)
    assert server.dashboard_builder is not None
