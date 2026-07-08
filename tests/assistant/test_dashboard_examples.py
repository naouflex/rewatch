"""Tests for dashboard example catalog."""

from rewatch.assistant.dashboard_examples import get_dashboard_example, list_dashboard_examples


def test_list_dashboard_examples():
    result = list_dashboard_examples()
    assert result["count"] >= 5
    assert any(item["id"] == "ethereum_defi" for item in result["examples"])


def test_list_dashboard_examples_search():
    result = list_dashboard_examples("weather")
    assert result["count"] >= 1
    assert all("weather" in item["summary"].lower() or "weather" in item["name"].lower() for item in result["examples"])


def test_get_dashboard_example():
    result = get_dashboard_example("viz_demo")
    assert result["id"] == "viz_demo"
    assert "spec_snippet" in result


def test_get_dashboard_example_unknown():
    result = get_dashboard_example("missing")
    assert "error" in result
    assert "known_ids" in result
