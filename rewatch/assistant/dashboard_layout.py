"""Dashboard grid layout helpers for the assistant."""

from __future__ import annotations

from typing import Any, Optional

# Matches client/app/config/dashboard-grid-options.js
DASHBOARD_GRID = {
    "columns": 12,
    "row_height_px": 50,
    "default_size_x": 6,
    "default_size_y": 3,
    "min_size_x": 2,
    "max_size_x": 12,
    "min_size_y": 2,
}

_POSITION_KEYS = frozenset(
    {"col", "row", "sizeX", "sizeY", "autoHeight", "minSizeX", "maxSizeX", "minSizeY", "maxSizeY"}
)


def widget_position(widget: dict[str, Any]) -> dict[str, Any]:
    options = widget.get("options") if isinstance(widget.get("options"), dict) else {}
    position = options.get("position") if isinstance(options.get("position"), dict) else {}
    return dict(position)


def normalize_widget_options(
    options: Optional[dict[str, Any]] = None,
    *,
    position: Optional[dict[str, Any]] = None,
) -> dict[str, Any]:
    """Ensure widget options use the nested ``options.position`` shape the UI expects."""
    normalized = dict(options or {})
    pos = dict(normalized.get("position") or {})

    for key in list(normalized.keys()):
        if key in _POSITION_KEYS:
            pos[key] = normalized.pop(key)

    if position:
        pos.update(position)

    pos.setdefault("col", 0)
    pos.setdefault("row", 0)
    pos.setdefault("sizeX", DASHBOARD_GRID["default_size_x"])
    pos.setdefault("sizeY", DASHBOARD_GRID["default_size_y"])
    pos.setdefault("minSizeX", DASHBOARD_GRID["min_size_x"])
    pos.setdefault("maxSizeX", DASHBOARD_GRID["max_size_x"])
    pos.setdefault("minSizeY", DASHBOARD_GRID["min_size_y"])
    pos.setdefault("maxSizeY", 1000)
    pos.setdefault("autoHeight", False)

    normalized["position"] = pos
    return normalized


def has_explicit_position(options: Optional[dict[str, Any]]) -> bool:
    if not options:
        return False
    if options.get("position"):
        return True
    return any(key in options for key in _POSITION_KEYS)


def suggest_next_position(widgets: list[dict[str, Any]]) -> dict[str, int]:
    """Place the next widget below existing ones (full width by default)."""
    if not widgets:
        return {"col": 0, "row": 0, "sizeX": DASHBOARD_GRID["default_size_x"], "sizeY": DASHBOARD_GRID["default_size_y"]}

    max_row_end = 0
    for widget in widgets:
        pos = widget_position(widget)
        row = int(pos.get("row") or 0)
        size_y = int(pos.get("sizeY") or DASHBOARD_GRID["default_size_y"])
        max_row_end = max(max_row_end, row + size_y)

    return {
        "col": 0,
        "row": max_row_end,
        "sizeX": DASHBOARD_GRID["default_size_x"],
        "sizeY": DASHBOARD_GRID["default_size_y"],
    }


def summarize_dashboard_layout(widgets: list[dict[str, Any]]) -> dict[str, Any]:
    """Compact layout summary for the model after get_dashboard / add_widget."""
    summary = []
    for widget in widgets or []:
        if not isinstance(widget, dict):
            continue
        pos = widget_position(widget)
        vis = widget.get("visualization") if isinstance(widget.get("visualization"), dict) else {}
        summary.append(
            {
                "widget_id": widget.get("id"),
                "visualization_id": vis.get("id"),
                "visualization_type": vis.get("type"),
                "visualization_name": vis.get("name"),
                "text_preview": (widget.get("text") or "")[:80] or None,
                "position": pos,
            }
        )
    return {
        "widget_count": len(summary),
        "widgets": summary,
        "grid": DASHBOARD_GRID,
        "placement_hint": (
            "Widget positions live in options.position: col (0–11), row (stacked rows), "
            "sizeX (width in columns, max 12), sizeY (height in row units). "
            "Omit position on add_widget_to_dashboard to auto-place below existing widgets."
        ),
    }


def enrich_dashboard_for_assistant(dashboard: dict[str, Any]) -> dict[str, Any]:
    widgets = dashboard.get("widgets") if isinstance(dashboard.get("widgets"), list) else []
    dashboard["layout_summary"] = summarize_dashboard_layout(widgets)
    dashboard["assistant_workflow"] = {
        "edit_widgets": "Use update_widget to change text or move/resize via options.position.",
        "add_chart": "create_visualization → add_widget_to_dashboard(visualization_id=...).",
        "publish": "Call update_dashboard with is_draft=false when the layout is ready.",
        "refresh_layout": "Call get_dashboard after changes to read widget ids and positions.",
    }
    if dashboard.get("is_draft"):
        dashboard["assistant_workflow"]["note"] = "Dashboard is still a draft — publish with update_dashboard(is_draft=false)."
    return dashboard
