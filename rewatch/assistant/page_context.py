"""Format client page context for the assistant system prompt."""

from __future__ import annotations

from typing import Any, Optional

# Maps route_id prefixes or exact ids to human-readable page kinds.
_ROUTE_LABELS: dict[str, str] = {
    "Home": "Home",
    "Queries.View": "Query",
    "Queries.New": "New query editor",
    "Queries.Source": "Query source editor",
    "Dashboards.ViewOrEdit": "Dashboard",
    "Dashboards.LegacyViewOrEdit": "Dashboard",
    "Alerts.View": "Alert",
    "Alerts.Edit": "Alert editor",
    "Alerts.New": "New alert",
    "DataSources.Edit": "Data source settings",
    "DataSources.List": "Data sources list",
    "Assistant": "Assistant full page",
}

_RESOURCE_HINTS: dict[str, tuple[str, str]] = {
    "query_id": ("query", "get_query"),
    "dashboard_id": ("dashboard", "get_dashboard"),
    "alert_id": ("alert", "get_alert"),
    "data_source_id": ("data source", "get_data_source"),
    "model_id": ("ML model", "get_ml_model"),
    "indexer_id": ("indexer", "get_indexer"),
    "destination_id": ("destination", "get_destination"),
    "prediction_id": ("prediction result", "get_predictions"),
}


def _route_label(route_id: Optional[str]) -> Optional[str]:
    if not route_id:
        return None
    if route_id in _ROUTE_LABELS:
        return _ROUTE_LABELS[route_id]
    if route_id.startswith("Queries."):
        return "Queries list"
    if route_id.startswith("Dashboards."):
        return "Dashboards list"
    if route_id.startswith("Alerts."):
        return "Alerts list"
    if route_id.startswith("MLModels.") or route_id.startswith("MLModel."):
        return "ML models"
    if route_id.startswith("Indexers."):
        return "Indexers"
    if route_id.startswith("Destinations."):
        return "Destinations"
    if route_id.startswith("Predictions."):
        return "Predictions"
    return route_id.replace(".", " ")


def format_page_context(page_context: Optional[dict[str, Any]]) -> str:
    """Turn client page context into a system-prompt appendix."""
    if not page_context or not isinstance(page_context, dict):
        return ""

    lines = [
        "Current UI context (the user is on this Rewatch page right now — treat it as the subject of ambiguous requests like "
        '"fix this", "explain this chart", or "update it"):'
    ]

    path = (page_context.get("path") or "").strip()
    if path:
        lines.append(f"- URL path: {path}")

    route_id = page_context.get("route_id")
    label = _route_label(route_id)
    if route_id:
        lines.append(f"- Route: {route_id}" + (f" ({label})" if label and label != route_id else ""))

    page_title = (page_context.get("page_title") or "").strip()
    if page_title:
        lines.append(f"- Page title: {page_title}")

    for field, (resource_label, tool_name) in _RESOURCE_HINTS.items():
        value = page_context.get(field)
        if value is None or value == "":
            continue
        lines.append(
            f"- Active {resource_label} ID: {value} — prefer {tool_name}({field}={value}) when the user refers to "
            '"this query/dashboard/alert/model" without specifying another ID.'
        )

    view = page_context.get("view")
    if view:
        lines.append(f"- View: {view}")

    if len(lines) == 1:
        return ""

    return "\n".join(lines)
