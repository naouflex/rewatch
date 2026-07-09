"""Human-readable labels for assistant tool activity."""

from __future__ import annotations

from typing import Any, Callable, Optional


def _truncate(value: str, limit: int = 72) -> str:
    text = (value or "").strip()
    if len(text) <= limit:
        return text
    return text[: limit - 1] + "…"


def _query_label(args: dict[str, Any]) -> str:
    if args.get("query_id"):
        return f"Running query #{args['query_id']}"
    if args.get("query_text"):
        return f"Running query: {_truncate(args['query_text'], 48)}"
    return "Running a query"


TOOL_START_LABELS: dict[str, Callable[[dict[str, Any]], str]] = {
    "search_queries": lambda a: f"Searching queries for “{_truncate(a.get('q', ''), 48)}”",
    "get_query": lambda a: f"Loading query #{a.get('query_id')}",
    "run_query": _query_label,
    "create_query": lambda a: f"Creating and validating query “{_truncate(a.get('name', ''), 40)}”",
    "update_query": lambda a: f"Updating and validating query #{a.get('query_id')}",
    "archive_query": lambda a: f"Archiving query #{a.get('query_id')}",
    "create_visualization": lambda a: f"Creating {a.get('type', 'viz')} “{_truncate(a.get('name', ''), 36)}” (after query check)",
    "update_visualization": lambda a: f"Updating visualization #{a.get('visualization_id')} (remap columns)",
    "get_visualization": lambda a: f"Diagnosing visualization #{a.get('visualization_id')}",
    "fix_query_visualizations": lambda a: f"Fixing visualizations on query #{a.get('query_id')}",
    "delete_visualization": lambda a: f"Deleting visualization #{a.get('visualization_id')}",
    "list_data_sources": lambda a: "Listing data sources",
    "list_query_runner_types": lambda a: "Browsing query runner types",
    "get_query_runner_type": lambda a: f"Loading docs for {a.get('type', 'query runner')} data sources",
    "list_visualization_types": lambda a: "Browsing visualization types",
    "get_visualization_type": lambda a: f"Loading {a.get('type', 'visualization')} options",
    "get_data_source": lambda a: f"Loading data source #{a.get('data_source_id')}",
    "get_data_source_schema": lambda a: f"Loading schema for data source #{a.get('data_source_id')}",
    "list_dashboards": lambda a: "Listing dashboards",
    "get_dashboard": lambda a: f"Loading dashboard #{a.get('dashboard_id')}",
    "create_dashboard": lambda a: f"Creating dashboard “{_truncate(a.get('name', ''), 40)}”",
    "update_dashboard": lambda a: f"Updating dashboard #{a.get('dashboard_id')}",
    "add_widget_to_dashboard": lambda a: f"Adding widget to dashboard #{a.get('dashboard_id')}",
    "update_widget": lambda a: f"Updating widget #{a.get('widget_id')}",
    "delete_widget": lambda a: f"Removing widget #{a.get('widget_id')}",
    "build_dashboard_from_spec": lambda a: (
        f"Building dashboard “{_truncate(a.get('name', ''), 40)}” "
        f"({len(a.get('queries') or [])} queries, {len(a.get('widgets') or [])} widgets)"
    ),
    "refresh_queries_and_wait": lambda a: f"Refreshing {len(a.get('query_ids') or [])} queries",
    "create_multi_visualization_query": lambda a: (
        f"Creating query “{_truncate(a.get('name', ''), 40)}” with {len(a.get('visualizations') or [])} visualizations"
    ),
    "list_alerts": lambda a: "Listing alerts",
    "get_alert": lambda a: f"Loading alert #{a.get('alert_id')}",
    "get_alert_template_guide": lambda a: "Loading alert template variables",
    "create_alert": lambda a: f"Creating alert “{_truncate(a.get('name', ''), 40)}”",
    "update_alert": lambda a: f"Updating alert #{a.get('alert_id')}",
    "delete_alert": lambda a: f"Deleting alert #{a.get('alert_id')}",
    "evaluate_alert": lambda a: f"Evaluating alert #{a.get('alert_id')}",
    "list_alert_subscriptions": lambda a: f"Listing subscriptions for alert #{a.get('alert_id')}",
    "subscribe_alert": lambda a: f"Subscribing destination #{a.get('destination_id')} to alert #{a.get('alert_id')}",
    "unsubscribe_alert": lambda a: f"Unsubscribing from alert #{a.get('alert_id')}",
    "list_destinations": lambda a: "Listing notification destinations",
    "get_destination": lambda a: f"Loading destination #{a.get('destination_id')}",
    "list_destination_types": lambda a: "Listing destination types",
    "get_destination_type": lambda a: f"Loading destination type {a.get('type', '')}",
    "create_destination": lambda a: f"Creating destination “{_truncate(a.get('name', ''), 40)}”",
    "update_destination": lambda a: f"Updating destination #{a.get('destination_id')}",
    "list_ml_models": lambda a: "Listing ML models",
    "get_ml_model": lambda a: f"Loading ML model #{a.get('model_id')}",
    "create_ml_model": lambda a: f"Creating ML model “{_truncate(a.get('name', ''), 40)}”",
    "update_ml_model": lambda a: f"Updating ML model #{a.get('model_id')}",
    "train_ml_model": lambda a: f"Starting training for model #{a.get('model_id')}",
    "predict_ml_model": lambda a: f"Starting prediction for model #{a.get('model_id')}",
    "get_predictions": lambda a: "Loading prediction results",
    "list_indexers": lambda a: "Listing indexers",
    "get_indexer": lambda a: f"Loading indexer #{a.get('indexer_id')}",
    "create_indexer": lambda a: f"Creating indexer “{_truncate(a.get('name', ''), 40)}”",
    "update_indexer": lambda a: f"Updating indexer #{a.get('indexer_id')}",
    "search_docs": lambda a: f"Searching docs for “{_truncate(a.get('q', ''), 48)}”",
    "get_docs_topic": lambda a: f"Opening docs topic “{a.get('topic_id')}”",
    "discover_public_sources": lambda a: (
        f"Discovering public {a.get('data_kind', 'json')} sources for “{_truncate(a.get('topic', ''), 48)}”"
    ),
    "web_search": lambda a: f"Searching the web for “{_truncate(a.get('q', ''), 56)}”",
    "fetch_url": lambda a: f"Reading {_truncate(a.get('url', ''), 64)}",
    "list_endpoints": lambda a: f"Browsing API endpoints{f' tagged {a.get('tag')!r}' if a.get('tag') else ''}",
    "describe_endpoint": lambda a: f"Describing {a.get('method', 'GET').upper()} {a.get('path', '')}",
    "call_api": lambda a: f"Calling {a.get('method', 'GET').upper()} {a.get('path', '')}",
    "list_dashboard_examples": lambda a: "Listing dashboard examples",
    "get_dashboard_example": lambda a: f"Loading dashboard example {a.get('id', '')!r}",
    "list_instance_examples": lambda a: "Listing production query/viz patterns",
    "get_instance_example": lambda a: f"Loading instance example {a.get('id', '')!r}",
}


def tool_start_label(tool_name: str, args: dict[str, Any]) -> str:
    formatter = TOOL_START_LABELS.get(tool_name)
    if formatter:
        try:
            return formatter(args)
        except Exception:
            pass
    return f"Using {tool_name.replace('_', ' ')}"


def _truncate(value: str, limit: int = 96) -> str:
    text = (value or "").strip()
    if len(text) <= limit:
        return text
    return text[: limit - 1] + "…"


def tool_result_summary(tool_name: str, payload: Any) -> Optional[str]:
    """Short human-readable outcome for decision graph tool nodes."""
    if not isinstance(payload, dict):
        return None

    if payload.get("error"):
        return _truncate(str(payload["error"]), 120)

    validation = payload.get("validation") or payload.get("query_validation")
    if isinstance(validation, dict):
        status = validation.get("status")
        if status == "error":
            return _truncate(validation.get("message") or "Validation failed", 120)
        if status == "ok":
            return "Validation passed"

    for key, prefix in (
        ("app_link", None),
        ("name", None),
        ("id", "#"),
        ("query_id", "Query #"),
        ("dashboard_id", "Dashboard #"),
        ("visualization_id", "Visualization #"),
        ("alert_id", "Alert #"),
        ("destination_id", "Destination #"),
        ("model_id", "Model #"),
    ):
        if payload.get(key) is not None and key != "app_link":
            value = payload[key]
            if prefix:
                return f"{prefix}{value}"
            return _truncate(str(value), 80)

    if tool_name == "discover_public_sources":
        count = payload.get("result_count")
        if isinstance(count, int):
            endpoints = payload.get("candidate_endpoints") or []
            endpoint_note = f", {len(endpoints)} endpoint{'s' if len(endpoints) != 1 else ''}" if endpoints else ""
            return f"{count} source{'s' if count != 1 else ''}{endpoint_note}"

    if isinstance(payload.get("results"), list):
        count = len(payload["results"])
        if tool_name == "web_search" and count:
            top = payload["results"][0]
            if isinstance(top, dict) and top.get("title"):
                return f"{count} result{'s' if count != 1 else ''} — {_truncate(top['title'], 56)}"
        return f"{count} result{'s' if count != 1 else ''}"

    if isinstance(payload.get("count"), int):
        return f"{payload['count']} item{'s' if payload['count'] != 1 else ''}"

    if tool_name == "fetch_url":
        if payload.get("openapi_detected"):
            return "OpenAPI spec detected"
        if payload.get("format") == "json":
            return "Fetched JSON endpoint"
        if payload.get("title"):
            return _truncate(payload["title"], 80)

    if tool_name == "web_search" and payload.get("title"):
        return _truncate(payload["title"], 80)

    return None
