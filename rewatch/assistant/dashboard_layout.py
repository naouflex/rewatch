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

_REQUIRED_POSITION_INT_KEYS = ("col", "row", "sizeX", "sizeY")

# Curated widget sizes matching the polished reference dashboards
# (KPI counters in 4-per-row grids, tall charts, full-width tables).
WIDGET_MIN_SIZE_BY_VIZ_TYPE = {
    "COUNTER": {"minSizeX": 1, "minSizeY": 1},
}

WIDGET_SIZE_BY_VIZ_TYPE = {
    "COUNTER": {"sizeX": 3, "sizeY": 3},
    "CHART": {"sizeX": 6, "sizeY": 8},
    "TABLE": {"sizeX": 12, "sizeY": 8},
    "PIVOT": {"sizeX": 12, "sizeY": 8},
    "MAP": {"sizeX": 6, "sizeY": 8},
    "CHOROPLETH": {"sizeX": 6, "sizeY": 8},
}

WIDGET_SIZE_BY_ROLE = {
    "title": {"sizeX": 12, "sizeY": 3},
    "section": {"sizeX": 12, "sizeY": 2},
    "kpi": {"sizeX": 3, "sizeY": 3},
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
    """Type-aware widget size: counters 3x3, charts 6x8, tables 12x8, text headers full width."""
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


def _coerce_int(value: Any, default: int) -> int:
    if value is None or value == "":
        return default
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def sanitize_widget_position(
    position: Optional[dict[str, Any]] = None,
    *,
    visualization_type: Optional[str] = None,
) -> dict[str, Any]:
    """Return a grid position dict with numeric col/row/sizeX/sizeY (never null)."""
    pos = dict(position or {})
    defaults = suggest_widget_size(visualization_type=visualization_type)
    sanitized = {
        "col": _coerce_int(pos.get("col"), 0),
        "row": _coerce_int(pos.get("row"), 0),
        "sizeX": _coerce_int(pos.get("sizeX"), defaults["sizeX"]),
        "sizeY": _coerce_int(pos.get("sizeY"), defaults["sizeY"]),
    }
    mins = widget_min_size(visualization_type=visualization_type)
    sanitized["minSizeX"] = _coerce_int(pos.get("minSizeX"), mins["minSizeX"])
    sanitized["maxSizeX"] = _coerce_int(pos.get("maxSizeX"), DASHBOARD_GRID["max_size_x"])
    sanitized["minSizeY"] = _coerce_int(pos.get("minSizeY"), mins["minSizeY"])
    sanitized["maxSizeY"] = _coerce_int(pos.get("maxSizeY"), 1000)
    sanitized["autoHeight"] = bool(pos.get("autoHeight", False))
    return sanitized


def find_invalid_widget_positions(widgets: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Detect widgets whose stored layout would crash ReactGridLayout."""
    issues = []
    for widget in widgets or []:
        if not isinstance(widget, dict):
            continue
        pos = widget_position(widget, sanitize=False)
        missing = [key for key in _REQUIRED_POSITION_INT_KEYS if pos.get(key) is None]
        invalid = [
            key
            for key in _REQUIRED_POSITION_INT_KEYS
            if pos.get(key) is not None and not isinstance(pos.get(key), (int, float))
        ]
        if missing or invalid:
            vis = widget.get("visualization") if isinstance(widget.get("visualization"), dict) else {}
            issues.append(
                {
                    "widget_id": widget.get("id"),
                    "visualization_name": vis.get("name"),
                    "missing_fields": missing,
                    "invalid_fields": invalid,
                    "position": pos,
                }
            )
    return issues


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
            pos = sanitize_widget_position(
                {
                    "col": explicit.get("col", 0),
                    "row": explicit.get("row", row),
                    "sizeX": explicit.get("sizeX", DASHBOARD_GRID["default_size_x"]),
                    "sizeY": explicit.get("sizeY", DASHBOARD_GRID["default_size_y"]),
                    "minSizeX": explicit.get("minSizeX"),
                    "maxSizeX": explicit.get("maxSizeX"),
                    "minSizeY": explicit.get("minSizeY"),
                    "maxSizeY": explicit.get("maxSizeY"),
                    "autoHeight": explicit.get("autoHeight"),
                },
                visualization_type=item.get("visualization_type"),
            )
            positions.append(
                {
                    "col": pos["col"],
                    "row": pos["row"],
                    "sizeX": pos["sizeX"],
                    "sizeY": pos["sizeY"],
                }
            )
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


def widget_position(widget: dict[str, Any], *, sanitize: bool = True) -> dict[str, Any]:
    options = widget.get("options") if isinstance(widget.get("options"), dict) else {}
    position = options.get("position") if isinstance(options.get("position"), dict) else {}
    if not sanitize:
        return dict(position)
    vis = widget.get("visualization") if isinstance(widget.get("visualization"), dict) else {}
    return sanitize_widget_position(position, visualization_type=vis.get("type"))


def widget_min_size(*, visualization_type: Optional[str] = None) -> dict[str, int]:
    """Per-viz minimum resize constraints (mirrors viz-lib minColumns/minRows)."""
    if visualization_type:
        mins = WIDGET_MIN_SIZE_BY_VIZ_TYPE.get(visualization_type.upper())
        if mins:
            return dict(mins)
    return {"minSizeX": DASHBOARD_GRID["min_size_x"], "minSizeY": DASHBOARD_GRID["min_size_y"]}


def normalize_widget_options(
    options: Optional[dict[str, Any]] = None,
    *,
    position: Optional[dict[str, Any]] = None,
    visualization_type: Optional[str] = None,
) -> dict[str, Any]:
    """Ensure widget options use the nested ``options.position`` shape the UI expects."""
    normalized = dict(options or {})
    pos = dict(normalized.get("position") or {})

    for key in list(normalized.keys()):
        if key in _POSITION_KEYS:
            pos[key] = normalized.pop(key)

    if position:
        pos.update(position)

    vis_type = visualization_type
    normalized["position"] = sanitize_widget_position(pos, visualization_type=vis_type)
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


def prepare_widget_options(
    widgets: list[dict[str, Any]],
    *,
    visualization_type: Optional[str] = None,
    text: Optional[str] = None,
    options: Optional[dict[str, Any]] = None,
) -> dict[str, Any]:
    """Normalize widget options and auto-place when no explicit position is given."""
    if has_explicit_position(options):
        return normalize_widget_options(options, visualization_type=visualization_type)
    return normalize_widget_options(
        options,
        position=suggest_next_position(widgets, visualization_type=visualization_type, text=text),
        visualization_type=visualization_type,
    )


def prepare_widget_options_for_update(
    widget: dict[str, Any],
    widgets: list[dict[str, Any]],
    *,
    visualization_type: Optional[str] = None,
    text: Optional[str] = None,
    options: Optional[dict[str, Any]] = None,
) -> dict[str, Any]:
    """Update path: keep the current grid slot unless the caller sets a new position."""
    if has_explicit_position(options):
        return normalize_widget_options(options, visualization_type=visualization_type)
    current = widget_position(widget, sanitize=False)
    if current and any(current.get(key) is not None for key in _REQUIRED_POSITION_INT_KEYS):
        merged = dict(options or {})
        merged.setdefault("position", dict(current))
        return normalize_widget_options(merged, visualization_type=visualization_type)
    return prepare_widget_options(
        widgets,
        visualization_type=visualization_type,
        text=text,
        options=options,
    )


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
        "layout_issues": find_invalid_widget_positions(widgets),
        "placement_hint": (
            "Widget positions live in options.position: col (0–11), row (stacked rows), "
            "sizeX (width in columns, max 12), sizeY (height in row units). "
            "Omit position on add_widget_to_dashboard to auto-place below existing widgets. "
            "All four fields must be numbers — null/missing values crash the dashboard UI."
        ),
    }


def enrich_dashboard_for_assistant(dashboard: dict[str, Any]) -> dict[str, Any]:
    widgets = dashboard.get("widgets") if isinstance(dashboard.get("widgets"), list) else []
    layout_summary = summarize_dashboard_layout(widgets)
    dashboard["layout_summary"] = layout_summary
    if layout_summary.get("layout_issues"):
        dashboard["layout_warnings"] = (
            "Some widgets have invalid grid positions (null col/sizeX/sizeY). "
            "Fix with update_widget using options.position or re-add via add_widget_to_dashboard."
        )
    dashboard["assistant_workflow"] = {
        "edit_widgets": "Use update_widget to change text or move/resize via options.position.",
        "add_chart": "create_visualization → add_widget_to_dashboard(visualization_id=...).",
        "publish": "Call update_dashboard with is_draft=false when the layout is ready.",
        "refresh_layout": "Call get_dashboard after changes to read widget ids and positions.",
    }
    if dashboard.get("is_draft"):
        dashboard["assistant_workflow"]["note"] = "Dashboard is still a draft — publish with update_dashboard(is_draft=false)."
    return dashboard
