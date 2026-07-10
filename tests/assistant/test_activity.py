"""Tests for assistant activity labels and summaries."""

from rewatch.assistant.activity import tool_preparing_label, tool_result_summary, tool_start_label


def test_tool_preparing_label():
    assert tool_preparing_label("run_query") == "Preparing run query…"


def test_run_query_ad_hoc_label_is_not_sql_specific():
    label = tool_start_label("run_query", {"query_text": "endpoint: protocols", "data_source_id": 10})
    assert label.startswith("Running query:")
    assert "SQL" not in label


def test_run_query_saved_id_label():
    label = tool_start_label("run_query", {"query_id": 15})
    assert label == "Running query #15"


def test_tool_result_summary_validation_ok():
    assert tool_result_summary("create_query", {"validation": {"status": "ok"}}) == "Validation passed"


def test_tool_result_summary_error():
    assert tool_result_summary("run_query", {"error": "Query failed"}) == "Query failed"


def test_tool_result_summary_count():
    assert tool_result_summary("list_data_sources", {"count": 2}) == "2 items"


def test_tool_result_summary_discover_public_sources():
    summary = tool_result_summary(
        "discover_public_sources",
        {
            "result_count": 3,
            "candidate_endpoints": [{"url": "https://api.example.com/data.json"}],
        },
    )
    assert summary == "3 sources, 1 endpoint"


def test_tool_result_summary_web_search_top_hit():
    summary = tool_result_summary(
        "web_search",
        {"results": [{"title": "SNCF Open Data API", "url": "https://example.com"}]},
    )
    assert summary.startswith("1 result")
    assert "SNCF Open Data API" in summary
