"""Tests for alert/destination assistant catalog."""

from rewatch.assistant import alert_catalog


def test_validate_alert_column_exact_match():
    result = alert_catalog.validate_alert_column("market_cap.usd", ["name", "market_cap.usd"])
    assert result["valid"] is True
    assert result["column"] == "market_cap.usd"


def test_validate_alert_column_case_insensitive_correction():
    result = alert_catalog.validate_alert_column("TVL", ["name", "tvl"])
    assert result["valid"] is True
    assert result["column"] == "tvl"
    assert result["corrected_from"] == "TVL"


def test_validate_alert_column_missing():
    result = alert_catalog.validate_alert_column("missing", ["a", "b"])
    assert result["valid"] is False
    assert "missing" in result["message"]


def test_build_alert_options_includes_templates():
    options = alert_catalog.build_alert_options(
        column="value",
        op=">",
        value=100,
        custom_subject="Alert {{ALERT_NAME}}",
        custom_body="Value {{QUERY_RESULT_VALUE}}",
        send_for_each_row=True,
    )
    assert options["custom_subject"] == "Alert {{ALERT_NAME}}"
    assert options["custom_body"] == "Value {{QUERY_RESULT_VALUE}}"
    assert options["send_for_each_row"] is True


def test_get_destination_type_webhook_has_examples():
    result = alert_catalog.get_destination_type("webhook")
    assert result["type"] == "webhook"
    assert result["template_location"] == "alert"
    assert "example_alert_templates" in result
    assert "mustache_variables" in result


def test_list_destination_types_catalog_merges_api():
    api_types = [{"type": "webhook", "name": "Webhook", "configuration_schema": {"type": "object"}}]
    result = alert_catalog.list_destination_types_catalog(api_types)
    assert result["count"] >= 1
    webhook = next(t for t in result["destination_types"] if t["type"] == "webhook")
    assert webhook["name"] == "Webhook"
    assert webhook["configuration_schema"] == api_types[0]["configuration_schema"]


def test_alert_workflow_lists_mustache_variables():
    workflow = alert_catalog.alert_workflow()
    assert "mustache_variables" in workflow
    assert any(v["name"] == "QUERY_RESULT_VALUE" for v in workflow["mustache_variables"])
