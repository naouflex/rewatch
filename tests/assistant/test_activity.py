from rewatch.assistant.activity import tool_start_label


def test_run_query_ad_hoc_label_is_not_sql_specific():
    label = tool_start_label("run_query", {"query_text": "endpoint: protocols", "data_source_id": 10})
    assert label.startswith("Running query:")
    assert "SQL" not in label


def test_run_query_saved_id_label():
    label = tool_start_label("run_query", {"query_id": 15})
    assert label == "Running query #15"
