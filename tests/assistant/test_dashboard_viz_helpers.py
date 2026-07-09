from rewatch.assistant.visualization_helpers import (
    build_visualization_hints,
    diagnose_visualization_options,
    enrich_visualizations_for_assistant,
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


def test_normalize_widget_options_counter_min_size():
    from rewatch.assistant.dashboard_layout import normalize_widget_options

    options = normalize_widget_options(visualization_type="COUNTER")
    assert options["position"]["minSizeX"] == 1
    assert options["position"]["minSizeY"] == 1


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


def test_resolve_column_name_matches_lagged_feature():
    columns = ["date", "FedFundsRate_lag_1", "VIX_lag_1", "BTC_Close_Price"]
    assert resolve_column_name("Date", columns) == "date"
    assert resolve_column_name("FedFundsRate", columns) == "FedFundsRate_lag_1"
    assert resolve_column_name("VIX", columns) == "VIX_lag_1"
    assert resolve_column_name("BTC_Price", columns) == "BTC_Close_Price"


def test_diagnose_visualization_options_flags_invalid_columns():
    columns = ["date", "SP500_Price"]
    diagnostics = diagnose_visualization_options(
        "CHART",
        {"columnMapping": {"Date": "x", "CPI_YoY": "y"}},
        columns,
        [{"date": "2018-01-01", "SP500_Price": 2500}],
    )
    assert diagnostics["is_healthy"] is False
    assert "Date" in diagnostics["invalid_columns"]
    assert "CPI_YoY" in diagnostics["invalid_columns"]


def test_enrich_visualizations_for_assistant_adds_options_health():
    visualizations = enrich_visualizations_for_assistant(
        [{"id": 1, "type": "CHART", "name": "Broken", "options": {"columnMapping": {"Date": "x", "CPI_YoY": "y"}}}],
        ["date", "SP500_Price"],
        [{"date": "2018-01-01", "SP500_Price": 2500}],
    )
    assert visualizations[0]["options_health"]["is_healthy"] is False
    assert "Date" in visualizations[0]["options_health"]["invalid_columns"]


def test_suggest_widget_size_is_type_aware():
    from rewatch.assistant.dashboard_layout import suggest_widget_size

    assert suggest_widget_size(visualization_type="COUNTER") == {"sizeX": 3, "sizeY": 3}
    assert suggest_widget_size(visualization_type="CHART") == {"sizeX": 6, "sizeY": 8}
    assert suggest_widget_size(visualization_type="TABLE") == {"sizeX": 12, "sizeY": 8}
    assert suggest_widget_size(text="# Big Title") == {"sizeX": 12, "sizeY": 3}
    assert suggest_widget_size(text="## Section") == {"sizeX": 12, "sizeY": 2}
    assert suggest_widget_size(visualization_type="CHART", layout_role="full") == {"sizeX": 12, "sizeY": 8}


def test_plan_dashboard_layout_packs_kpi_row_and_sections():
    from rewatch.assistant.dashboard_layout import plan_dashboard_layout

    positions = plan_dashboard_layout(
        [
            {"text": "# Title"},
            {"visualization_type": "COUNTER"},
            {"visualization_type": "COUNTER"},
            {"visualization_type": "COUNTER"},
            {"visualization_type": "COUNTER"},
            {"visualization_type": "COUNTER"},
            {"visualization_type": "TABLE"},
        ]
    )
    # Title takes the full first band.
    assert positions[0] == {"col": 0, "row": 0, "sizeX": 12, "sizeY": 3}
    # First four counters pack into one row below the title.
    kpi_row = positions[1]["row"]
    assert [p["col"] for p in positions[1:5]] == [0, 3, 6, 9]
    assert all(p["row"] == kpi_row for p in positions[1:5])
    # Fifth counter wraps to the next row; the table goes below it, full width.
    assert positions[5]["row"] > kpi_row
    assert positions[6]["sizeX"] == 12
    assert positions[6]["row"] > positions[5]["row"]


def test_plan_dashboard_layout_respects_explicit_position():
    from rewatch.assistant.dashboard_layout import plan_dashboard_layout

    positions = plan_dashboard_layout(
        [
            {"visualization_type": "CHART", "position": {"col": 6, "row": 10, "sizeX": 6, "sizeY": 4}},
            {"visualization_type": "CHART"},
        ]
    )
    assert positions[0] == {"col": 6, "row": 10, "sizeX": 6, "sizeY": 4}
    assert positions[1]["row"] >= 14


def test_suggest_next_position_packs_counters_side_by_side():
    from rewatch.assistant.dashboard_layout import suggest_next_position

    widgets = [
        {"options": {"position": {"col": 0, "row": 0, "sizeX": 3, "sizeY": 3}}},
    ]
    pos = suggest_next_position(widgets, visualization_type="COUNTER")
    assert pos == {"col": 3, "row": 0, "sizeX": 3, "sizeY": 3}

    # A chart after a counter starts a new row with chart sizing.
    pos = suggest_next_position(widgets, visualization_type="CHART")
    assert pos == {"col": 0, "row": 3, "sizeX": 6, "sizeY": 8}


def test_suggest_next_position_defaults_unchanged_without_type():
    from rewatch.assistant.dashboard_layout import suggest_next_position

    assert suggest_next_position([]) == {"col": 0, "row": 0, "sizeX": 6, "sizeY": 3}


def test_sanitize_widget_position_coerces_nulls():
    from rewatch.assistant.dashboard_layout import sanitize_widget_position

    pos = sanitize_widget_position(
        {"col": None, "row": 5, "sizeX": None, "sizeY": None},
        visualization_type="CHART",
    )
    assert pos == {
        "col": 0,
        "row": 5,
        "sizeX": 6,
        "sizeY": 8,
        "minSizeX": 2,
        "maxSizeX": 12,
        "minSizeY": 2,
        "maxSizeY": 1000,
        "autoHeight": False,
    }


def test_find_invalid_widget_positions_detects_missing_col():
    from rewatch.assistant.dashboard_layout import find_invalid_widget_positions

    issues = find_invalid_widget_positions(
        [{"id": 9, "options": {"position": {"row": 1, "sizeX": 6, "sizeY": 3}}}]
    )
    assert issues[0]["widget_id"] == 9
    assert "col" in issues[0]["missing_fields"]


def test_suggest_next_position_tolerates_broken_existing_widgets():
    from rewatch.assistant.dashboard_layout import suggest_next_position

    widgets = [{"options": {"position": {"row": 10, "sizeX": None, "sizeY": 8}}}]
    pos = suggest_next_position(widgets, visualization_type="CHART")
    assert pos["col"] == 0
    assert pos["row"] == 18
    assert pos["sizeX"] == 6
    assert pos["sizeY"] == 8


def test_prepare_widget_options_auto_places():
    from rewatch.assistant.dashboard_layout import prepare_widget_options

    options = prepare_widget_options(
        [{"id": 1, "options": {"position": {"col": 0, "row": 0, "sizeX": 12, "sizeY": 3}}}],
        visualization_type="CHART",
    )
    assert options["position"]["row"] == 3
    assert options["position"]["sizeX"] == 6


def test_prepare_widget_options_for_update_preserves_position():
    from rewatch.assistant.dashboard_layout import prepare_widget_options_for_update

    widget = {"id": 5, "options": {"position": {"col": 6, "row": 12, "sizeX": 6, "sizeY": 8}}}
    options = prepare_widget_options_for_update(widget, [widget], visualization_type="CHART", options={})
    assert options["position"]["col"] == 6
    assert options["position"]["row"] == 12


def test_prepare_widget_options_for_update_coerces_partial_position():
    from rewatch.assistant.dashboard_layout import prepare_widget_options_for_update

    widget = {"id": 5, "options": {"position": {"col": None, "row": 12, "sizeX": None, "sizeY": 8}}}
    options = prepare_widget_options_for_update(
        widget,
        [widget],
        visualization_type="CHART",
        options={"position": {"col": None, "row": 12}},
    )
    assert options["position"]["col"] == 0
    assert options["position"]["sizeX"] == 6
    assert options["position"]["row"] == 12


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
