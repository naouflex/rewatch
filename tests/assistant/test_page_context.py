"""Tests for assistant page context formatting."""

from rewatch.assistant.page_context import format_page_context


def test_format_page_context_empty():
    assert format_page_context(None) == ""
    assert format_page_context({}) == ""


def test_format_page_context_query_page():
    text = format_page_context(
        {
            "path": "/queries/42",
            "route_id": "Queries.View",
            "page_title": "Daily signups",
            "query_id": 42,
        }
    )
    assert "URL path: /queries/42" in text
    assert "Queries.View" in text
    assert "query_id=42" in text


def test_format_page_context_dashboard_page():
    text = format_page_context(
        {
            "path": "/dashboards/7-revenue",
            "route_id": "Dashboards.ViewOrEdit",
            "dashboard_id": 7,
        }
    )
    assert "dashboard_id=7" in text
    assert "get_dashboard" in text
