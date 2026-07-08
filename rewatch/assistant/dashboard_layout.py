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

# Curated widget sizes matching the polished reference dashboards
# (KPI counters in 4-per-row grids, tall charts, full-width tables).
WIDGET_SIZE_BY_VIZ_TYPE = {
    "COUNTER": {"sizeX": 3, "sizeY": 8},
    "CHART": {"sizeX": 6, "sizeY": 8},
    "TABLE": {"sizeX": 12, "sizeY": 8},
    "PIVOT": {"sizeX": 12, "sizeY": 8},
    "MAP": {"sizeX": 6, "sizeY": 8},
    "CHOROPLETH": {"sizeX": 6, "sizeY": 8},
}

WIDGET_SIZE_BY_ROLE = {
    "title": {"sizeX": 12, "sizeY": 3},
    "section": {"sizeX": 12, "sizeY": 2},
    "kpi": {"sizeX": 3, "sizeY": 8},
    "third": {"sizeX": 4, "sizeY": 8},
    "half": {"sizeX": 6, "sizeY": 8},
    "full": {"sizeX": 12, "sizeY": 8},
}


def suggest_widget_size(
    *,
    visualization_type: Optional[str] = None,
    text: Optional[str] = None,
    layout_role: Optional[str] = None,
) -> dict[str, int]:
    """Type-aware widget size: counters 3x8, charts 6x8, tables 12x8, text headers full width."""
    if layout_role:
        size = WIDGET_SIZE_BY_ROLE.get(layout_role.lower())
        if size:
            return dict(size)
    if text is not None:
        role = "title" if text.lstrip().startswith("# ") else "section"
        return dict(WIDGET_SIZE_BY_ROLE[role])
    if visualization_type:
        size = WIDGET_SIZE_BY_VIZ_TYPE.get(visualization_type.upper())
        if size:
            return dict(size)
    return {"sizeX": DASHBOARD_GRID["default_size_x"], "sizeY": DASHBOARD_GRID["default_size_y"]}


def plan_dashboard_layout(items: list[dict[str, Any]]) -> list[dict[str, int]]:
    """Compute grid positions for a full widget list.

    Each item: {"visualization_type"?, "text"?, "role"?, "position"?}. Explicit
    positions are respected; the rest are packed left-to-right into 12-column
    rows using type-aware sizes (KPI rows of four counters, side-by-side
    charts, full-width tables and section headers).
    """
    positions: list[dict[str, int]] = []
    row = 0
    col = 0
    row_height = 0

    def flush_row() -> None:
        nonlocal row, col, row_height
        if col > 0:
            row += row_height
            col = 0
            row_height = 0

    for item in items:
        explicit = item.get("position")
        if isinstance(explicit, dict) and explicit:
            pos = {
                "col": int(explicit.get("col", 0)),
                "row": int(explicit.get("row", row)),
                "sizeX": int(explicit.get("sizeX", DASHBOARD_GRID["default_size_x"])),
                "sizeY": int(explicit.get("sizeY", DASHBOARD_GRID["default_size_y"])),
            }
            positions.append(pos)
            flush_row()
            row = max(row, pos["row"] + pos["sizeY"])
            continue

        size = suggest_widget_size(
            visualization_type=item.get("visualization_type"),
            text=item.get("text"),
            layout_role=item.get("role"),
        )
        if col + size["sizeX"] > DASHBOARD_GRID["columns"]:
            flush_row()
        positions.append({"col": col, "row": row, **size})
        col += size["sizeX"]
        row_height = max(row_height, size["sizeY"])
        if col >= DASHBOARD_GRID["columns"]:
            flush_row()

    return positions


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


def suggest_next_position(
    widgets: list[dict[str, Any]],
    *,
    visualization_type: Optional[str] = None,
    text: Optional[str] = None,
) -> dict[str, int]:
    """Place the next widget below existing ones with a type-aware size.

    Counters pack side-by-side (4 per row) when the previous widget is also a
    counter and there is horizontal room; everything else starts a new row.
    """
    size = suggest_widget_size(visualization_type=visualization_type, text=text)
    if not widgets:
        return {"col": 0, "row": 0, **size}

    max_row_end = 0
    last_pos: dict[str, Any] = {}
    last_row_start = 0
    for widget in widgets:
        pos = widget_position(widget)
        row = int(pos.get("row") or 0)
        size_y = int(pos.get("sizeY") or DASHBOARD_GRID["default_size_y"])
        row_end = row + size_y
        if row_end > max_row_end or (row_end == max_row_end and row >= last_row_start):
            max_row_end = row_end
            last_row_start = row
            last_pos = pos

    if (visualization_type or "").upper() == "COUNTER" and last_pos:
        last_col_end = int(last_pos.get("col") or 0) + int(last_pos.get("sizeX") or 0)
        same_size = int(last_pos.get("sizeY") or 0) == size["sizeY"]
        if same_size and last_col_end + size["sizeX"] <= DASHBOARD_GRID["columns"]:
            return {"col": last_col_end, "row": last_row_start, **size}

    return {"col": 0, "row": max_row_end, **size}


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
