"""Human-readable labels for assistant tool activity."""

from __future__ import annotations

from typing import Any, Callable


def _truncate(value: str, limit: int = 72) -> str:
    text = (value or "").strip()
    if len(text) <= limit:
        return text
    return text[: limit - 1] + "…"


def _query_label(args: dict[str, Any]) -> str:
    if args.get("query_id"):
        return f"Running query #{args['query_id']}"
    if args.get("query_text"):
        return f"Running SQL: {_truncate(args['query_text'], 48)}"
    return "Running a query"


TOOL_START_LABELS: dict[str, Callable[[dict[str, Any]], str]] = {
    "search_queries": lambda a: f"Searching queries for “{_truncate(a.get('q', ''), 48)}”",
    "get_query": lambda a: f"Loading query #{a.get('query_id')}",
    "run_query": _query_label,
    "create_query": lambda a: f"Creating and validating query “{_truncate(a.get('name', ''), 40)}”",
    "update_query": lambda a: f"Updating and validating query #{a.get('query_id')}",
    "archive_query": lambda a: f"Archiving query #{a.get('query_id')}",
    "create_visualization": lambda a: f"Creating {a.get('type', 'viz')} “{_truncate(a.get('name', ''), 36)}” (after query check)",
    "update_visualization": lambda a: f"Updating visualization #{a.get('visualization_id')}",
    "delete_visualization": lambda a: f"Deleting visualization #{a.get('visualization_id')}",
    "list_data_sources": lambda a: "Listing data sources",
    "get_data_source_schema": lambda a: f"Loading schema for data source #{a.get('data_source_id')}",
    "list_dashboards": lambda a: "Listing dashboards",
    "get_dashboard": lambda a: f"Loading dashboard #{a.get('dashboard_id')}",
    "create_dashboard": lambda a: f"Creating dashboard “{_truncate(a.get('name', ''), 40)}”",
    "update_dashboard": lambda a: f"Updating dashboard #{a.get('dashboard_id')}",
    "add_widget_to_dashboard": lambda a: f"Adding widget to dashboard #{a.get('dashboard_id')}",
    "update_widget": lambda a: f"Updating widget #{a.get('widget_id')}",
    "delete_widget": lambda a: f"Removing widget #{a.get('widget_id')}",
    "list_alerts": lambda a: "Listing alerts",
    "get_alert": lambda a: f"Loading alert #{a.get('alert_id')}",
    "create_alert": lambda a: f"Creating alert “{_truncate(a.get('name', ''), 40)}”",
    "update_alert": lambda a: f"Updating alert #{a.get('alert_id')}",
    "delete_alert": lambda a: f"Deleting alert #{a.get('alert_id')}",
    "list_destinations": lambda a: "Listing notification destinations",
    "list_destination_types": lambda a: "Listing destination types",
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
    "web_search": lambda a: f"Searching the web for “{_truncate(a.get('q', ''), 56)}”",
    "fetch_url": lambda a: f"Reading {_truncate(a.get('url', ''), 64)}",
}


def tool_start_label(tool_name: str, args: dict[str, Any]) -> str:
    formatter = TOOL_START_LABELS.get(tool_name)
    if formatter:
        try:
            return formatter(args)
        except Exception:
            pass
    return f"Using {tool_name.replace('_', ' ')}"
