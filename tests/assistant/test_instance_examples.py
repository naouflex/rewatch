"""Tests for production instance example catalog."""

from rewatch.assistant.instance_examples import (
    get_instance_example,
    list_instance_examples,
)


def test_list_instance_examples_returns_categories():
    result = list_instance_examples()
    assert result["count"] >= 10
    assert "query_results" in result["categories"]
    assert "python" in result["categories"]
    assert result["stats"]["totals"]["queries"] == 951


def test_list_instance_examples_filters_by_category():
    result = list_instance_examples(category="evmlogs")
    assert result["count"] >= 1
    assert all(item["category"] == "evmlogs" for item in result["examples"])


def test_get_instance_example_returns_query_snippet():
    result = get_instance_example("results_derived_cte")
    assert result["id"] == "results_derived_cte"
    assert "query_1130" in result["query_example"]
    assert result["visualization_example"]["chart_type"] == "area"


def test_get_instance_example_unknown_id():
    result = get_instance_example("nonexistent")
    assert "error" in result
    assert "known_ids" in result
