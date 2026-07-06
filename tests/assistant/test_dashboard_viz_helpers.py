from rewatch.assistant.visualization_helpers import (
    build_visualization_hints,
    normalize_visualization_options,
    resolve_column_name,
    suggest_chart_options,
    suggest_counter_options,
)


def test_normalize_widget_options_nests_flat_position():
    from rewatch.assistant.dashboard_layout import normalize_widget_options

    options = normalize_widget_options({"col": 3, "row": 6, "sizeX": 12, "sizeY": 4})
    assert options["position"]["col"] == 3
    assert options["position"]["row"] == 6
    assert options["position"]["sizeX"] == 12
    assert "col" not in options


def test_suggest_chart_options_maps_date_and_numeric():
    columns = ["date", "tvl", "name"]
    rows = [{"date": "2024-01-01", "tvl": 100, "name": "eth"}]
    options = suggest_chart_options(columns, rows, series_type="line")
    assert options["columnMapping"]["date"] == "x"
    assert options["columnMapping"]["tvl"] == "y"
    assert options["globalSeriesType"] == "line"


def test_suggest_chart_options_multi_numeric_y():
    columns = ["date", "tvl", "volume"]
    rows = [{"date": "2024-01-01", "tvl": 100, "volume": 50}]
    options = suggest_chart_options(columns, rows)
    y_cols = [name for name, role in options["columnMapping"].items() if role == "y"]
    assert set(y_cols) == {"tvl", "volume"}


def test_resolve_column_name_fuzzy_match():
    columns = ["market_cap.usd", "name"]
    assert resolve_column_name("market_cap.usd", columns) == "market_cap.usd"
    assert resolve_column_name("Market_Cap.USD", columns) == "market_cap.usd"
    assert resolve_column_name("market cap usd", columns) == "market_cap.usd"


def test_normalize_chart_options_fixes_wrong_mapping():
    columns = ["date", "tvl"]
    rows = [{"date": "2024-01-01", "tvl": 100}]
    options, corrections = normalize_visualization_options(
        "CHART",
        {"globalSeriesType": "line", "columnMapping": {"timestamp": "x", "value": "y"}},
        columns,
        rows,
    )
    assert options["columnMapping"]["date"] == "x"
    assert options["columnMapping"]["tvl"] == "y"
    assert any("timestamp" in c or "value" in c for c in corrections)


def test_normalize_chart_options_rejects_placeholders():
    columns = ["created_at", "total_usd"]
    rows = [{"created_at": "2024-01-01", "total_usd": 42}]
    options, _ = normalize_visualization_options(
        "CHART",
        {"columnMapping": {"<x_column>": "x", "<y_column>": "y"}},
        columns,
        rows,
    )
    assert options["columnMapping"]["created_at"] == "x"
    assert options["columnMapping"]["total_usd"] == "y"


def test_suggest_counter_options_picks_numeric_column():
    options = suggest_counter_options(["name", "total_usd"], [{"name": "a", "total_usd": 42}])
    assert options["counterColName"] == "total_usd"


def test_normalize_counter_options_fixes_wrong_column():
    columns = ["name", "market_cap.usd"]
    rows = [{"name": "eth", "market_cap.usd": 123}]
    options, corrections = normalize_visualization_options(
        "COUNTER",
        {"counterColName": "market_cap"},
        columns,
        rows,
    )
    assert options["counterColName"] == "market_cap.usd"
    assert corrections


def test_build_visualization_hints_includes_columns():
    hints = build_visualization_hints(["date", "tvl"], [{"date": 1, "tvl": 2}])
    assert hints["columns"] == ["date", "tvl"]
    assert hints["recommended"]["CHART"]["omit_options"] is True
    assert hints["recommended"]["CHART"]["suggested_options"]["columnMapping"]["tvl"] == "y"


def test_enrich_dashboard_adds_layout_summary():
    from rewatch.assistant.dashboard_layout import enrich_dashboard_for_assistant

    dashboard = enrich_dashboard_for_assistant(
        {
            "id": 1,
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
    )
    assert dashboard["layout_summary"]["widget_count"] == 1
    assert dashboard["layout_summary"]["widgets"][0]["widget_id"] == 10
    assert "publish" in dashboard["assistant_workflow"]["note"]
