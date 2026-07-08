"""SVG preview images for assistant chat illustrations."""

from __future__ import annotations

import html
import math
from typing import Any, Optional

from rewatch import models
from rewatch.assistant.dashboard_layout import widget_position

WIDTH = 520
HEIGHT = 300
PADDING = 16
BG = "#f8fafc"
TEXT = "#1e293b"
MUTED = "#64748b"
ACCENT = "#2563eb"
GRID = "#e2e8f0"
CARD = "#ffffff"


def preview_path(base_url: str, resource: str, resource_id: int | str) -> str:
    base = base_url.rstrip("/")
    return f"{base}/api/assistant/previews/{resource}/{resource_id}"


def _escape(value: Any) -> str:
    return html.escape(str(value if value is not None else ""))


def _query_rows(query: models.Query) -> tuple[list[str], list[dict[str, Any]]]:
    result = query.latest_query_data
    if not result or not result.data:
        return [], []
    columns = [col.get("name", "") for col in result.data.get("columns", [])]
    rows = result.data.get("rows", []) or []
    return columns, rows


def _svg_open(title: str, subtitle: Optional[str] = None) -> list[str]:
    lines = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{WIDTH}" height="{HEIGHT}" viewBox="0 0 {WIDTH} {HEIGHT}">',
        f'<rect width="100%" height="100%" fill="{BG}" rx="12"/>',
        f'<text x="{PADDING}" y="28" fill="{TEXT}" font-family="Inter, Arial, sans-serif" font-size="15" font-weight="600">{_escape(title)}</text>',
    ]
    if subtitle:
        lines.append(
            f'<text x="{PADDING}" y="48" fill="{MUTED}" font-family="Inter, Arial, sans-serif" font-size="12">{_escape(subtitle)}</text>'
        )
    return lines


def _svg_close(lines: list[str]) -> str:
    lines.append("</svg>")
    return "\n".join(lines)


def _empty_state(title: str, message: str) -> str:
    lines = _svg_open(title)
    lines.append(
        f'<text x="{WIDTH / 2}" y="{HEIGHT / 2}" fill="{MUTED}" font-family="Inter, Arial, sans-serif" font-size="13" text-anchor="middle">{_escape(message)}</text>'
    )
    return _svg_close(lines)


def render_table_svg(title: str, columns: list[str], rows: list[dict[str, Any]], *, subtitle: Optional[str] = None) -> str:
    if not columns:
        return _empty_state(title, "Run the query to see a table preview.")

    display_cols = columns[:5]
    display_rows = rows[:6]
    lines = _svg_open(title, subtitle)
    top = 62 if subtitle else 52
    col_width = (WIDTH - PADDING * 2) / max(len(display_cols), 1)
    row_height = 24

    for index, column in enumerate(display_cols):
        x = PADDING + index * col_width
        lines.append(f'<rect x="{x}" y="{top}" width="{col_width - 2}" height="{row_height}" fill="{GRID}"/>')
        lines.append(
            f'<text x="{x + 8}" y="{top + 16}" fill="{TEXT}" font-family="Inter, Arial, sans-serif" font-size="11" font-weight="600">{_escape(column[:18])}</text>'
        )

    for row_index, row in enumerate(display_rows):
        y = top + row_height * (row_index + 1)
        for col_index, column in enumerate(display_cols):
            x = PADDING + col_index * col_width
            fill = CARD if row_index % 2 == 0 else BG
            lines.append(f'<rect x="{x}" y="{y}" width="{col_width - 2}" height="{row_height}" fill="{fill}" stroke="{GRID}"/>')
            value = row.get(column, "")
            lines.append(
                f'<text x="{x + 8}" y="{y + 16}" fill="{TEXT}" font-family="Inter, Arial, sans-serif" font-size="11">{_escape(value)[:22]}</text>'
            )

    if len(rows) > len(display_rows) or len(columns) > len(display_cols):
        lines.append(
            f'<text x="{PADDING}" y="{HEIGHT - 12}" fill="{MUTED}" font-family="Inter, Arial, sans-serif" font-size="11">Showing {len(display_rows)} of {len(rows)} rows</text>'
        )
    return _svg_close(lines)


def _chart_columns(options: dict[str, Any], columns: list[str]) -> tuple[Optional[str], list[str]]:
    mapping = options.get("columnMapping") or {}
    x_col = next((name for name, role in mapping.items() if role == "x"), columns[0] if columns else None)
    y_cols = [name for name, role in mapping.items() if role == "y"]
    if not y_cols:
        y_cols = [col for col in columns if col != x_col][:1]
    return x_col, y_cols


def render_chart_svg(title: str, columns: list[str], rows: list[dict[str, Any]], options: dict[str, Any]) -> str:
    if not rows:
        return _empty_state(title, "Run the query to see a chart preview.")

    x_col, y_cols = _chart_columns(options or {}, columns)
    y_col = y_cols[0] if y_cols else None
    if not x_col or not y_col:
        return render_table_svg(title, columns, rows, subtitle="Chart preview unavailable — showing table")

    series_type = (options or {}).get("globalSeriesType") or "column"
    points = rows[:12]
    labels = [_escape(row.get(x_col, ""))[:10] for row in points]
    values: list[float] = []
    for row in points:
        raw = row.get(y_col, 0)
        try:
            values.append(float(raw))
        except (TypeError, ValueError):
            values.append(0.0)

    max_value = max(values) or 1.0
    lines = _svg_open(title, series_type.title())
    chart_top = 62
    chart_height = HEIGHT - chart_top - 36
    chart_width = WIDTH - PADDING * 2
    bar_gap = 8
    bar_width = max(12, (chart_width - bar_gap * (len(values) + 1)) / max(len(values), 1))

    lines.append(
        f'<rect x="{PADDING}" y="{chart_top}" width="{chart_width}" height="{chart_height}" fill="{CARD}" stroke="{GRID}" rx="8"/>'
    )

    if series_type in ("line", "area", "scatter"):
        coords = []
        for index, value in enumerate(values):
            x = PADDING + bar_gap + index * (bar_width + bar_gap) + bar_width / 2
            y = chart_top + chart_height - (value / max_value) * (chart_height - 20) - 10
            coords.append((x, y))
        if len(coords) >= 2:
            path = "M " + " L ".join(f"{x:.1f} {y:.1f}" for x, y in coords)
            if series_type == "area":
                base_y = chart_top + chart_height - 10
                path = f"{path} L {coords[-1][0]:.1f} {base_y:.1f} L {coords[0][0]:.1f} {base_y:.1f} Z"
                lines.append(f'<path d="{path}" fill="{ACCENT}33" stroke="none"/>')
                path = "M " + " L ".join(f"{x:.1f} {y:.1f}" for x, y in coords)
            lines.append(f'<path d="{path}" fill="none" stroke="{ACCENT}" stroke-width="2.5"/>')
        for (x, y), label in zip(coords, labels):
            lines.append(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="3.5" fill="{ACCENT}"/>')
            lines.append(
                f'<text x="{x:.1f}" y="{chart_top + chart_height + 14}" fill="{MUTED}" font-family="Inter, Arial, sans-serif" font-size="10" text-anchor="middle">{label}</text>'
            )
    elif series_type == "pie" and values:
        total = sum(abs(v) for v in values) or 1.0
        cx = WIDTH / 2
        cy = chart_top + chart_height / 2
        radius = min(chart_width, chart_height) / 2 - 18
        start = -math.pi / 2
        palette = ["#2563eb", "#7c3aed", "#0891b2", "#059669", "#d97706", "#dc2626"]
        for index, value in enumerate(values):
            angle = (abs(value) / total) * math.pi * 2
            end = start + angle
            x1 = cx + radius * math.cos(start)
            y1 = cy + radius * math.sin(start)
            x2 = cx + radius * math.cos(end)
            y2 = cy + radius * math.sin(end)
            large = 1 if angle > math.pi else 0
            color = palette[index % len(palette)]
            lines.append(
                f'<path d="M {cx:.1f} {cy:.1f} L {x1:.1f} {y1:.1f} A {radius:.1f} {radius:.1f} 0 {large} 1 {x2:.1f} {y2:.1f} Z" fill="{color}"/>'
            )
            start = end
    else:
        for index, value in enumerate(values):
            x = PADDING + bar_gap + index * (bar_width + bar_gap)
            bar_height = (value / max_value) * (chart_height - 20)
            y = chart_top + chart_height - bar_height - 10
            lines.append(f'<rect x="{x:.1f}" y="{y:.1f}" width="{bar_width:.1f}" height="{bar_height:.1f}" fill="{ACCENT}" rx="4"/>')
            lines.append(
                f'<text x="{x + bar_width / 2:.1f}" y="{chart_top + chart_height + 14}" fill="{MUTED}" font-family="Inter, Arial, sans-serif" font-size="10" text-anchor="middle">{labels[index]}</text>'
            )

    return _svg_close(lines)


def render_counter_svg(title: str, columns: list[str], rows: list[dict[str, Any]], options: dict[str, Any]) -> str:
    if not rows:
        return _empty_state(title, "Run the query to see a counter preview.")

    opts = options or {}
    column = opts.get("counterColName") or (columns[0] if columns else None)
    row_index = max(int(opts.get("rowNumber") or 1) - 1, 0)
    row = rows[min(row_index, len(rows) - 1)]
    value = row.get(column, "") if column else ""
    label = opts.get("counterLabel") or column or "Value"

    lines = _svg_open(title, "Counter")
    lines.append(
        f'<text x="{WIDTH / 2}" y="{HEIGHT / 2 + 8}" fill="{ACCENT}" font-family="Inter, Arial, sans-serif" font-size="42" font-weight="700" text-anchor="middle">{_escape(value)}</text>'
    )
    lines.append(
        f'<text x="{WIDTH / 2}" y="{HEIGHT / 2 + 38}" fill="{MUTED}" font-family="Inter, Arial, sans-serif" font-size="13" text-anchor="middle">{_escape(label)}</text>'
    )
    return _svg_close(lines)


def render_visualization_svg(visualization: models.Visualization, query: models.Query) -> str:
    columns, rows = _query_rows(query)
    title = visualization.name or visualization.type
    options = visualization.options or {}
    viz_type = (visualization.type or "TABLE").upper()

    if viz_type == "CHART":
        return render_chart_svg(title, columns, rows, options)
    if viz_type == "COUNTER":
        return render_counter_svg(title, columns, rows, options)
    return render_table_svg(title, columns, rows, subtitle=query.name)


def render_query_svg(query: models.Query) -> str:
    columns, rows = _query_rows(query)
    visualizations = list(query.visualizations or [])
    preferred = next((vis for vis in visualizations if (vis.type or "").upper() != "TABLE"), None)
    if preferred:
        return render_visualization_svg(preferred, query)
    return render_table_svg(query.name or f"Query {query.id}", columns, rows)


def _widget_layout(widget: models.Widget) -> tuple[int, int, int, int]:
    pos = widget_position({"options": widget.options or {}})
    return (
        int(pos.get("col") or 0),
        int(pos.get("row") or 0),
        max(int(pos.get("sizeX") or 3), 1),
        max(int(pos.get("sizeY") or 2), 1),
    )


def render_dashboard_svg(dashboard: models.Dashboard) -> str:
    widgets = list(dashboard.widgets)
    lines = _svg_open(dashboard.name or f"Dashboard {dashboard.id}", f"{len(widgets)} widgets")
    grid_cols = 12
    grid_top = 62
    grid_height = HEIGHT - grid_top - 16
    cell_width = (WIDTH - PADDING * 2) / grid_cols

    lines.append(
        f'<rect x="{PADDING}" y="{grid_top}" width="{WIDTH - PADDING * 2}" height="{grid_height}" fill="{CARD}" stroke="{GRID}" rx="8"/>'
    )

    if not widgets:
        lines.append(
            f'<text x="{WIDTH / 2}" y="{grid_top + grid_height / 2}" fill="{MUTED}" font-family="Inter, Arial, sans-serif" font-size="13" text-anchor="middle">No widgets yet</text>'
        )
        return _svg_close(lines)

    layouts = [_widget_layout(widget) for widget in widgets[:12]]
    max_row_end = max(row + size_y for _, row, _, size_y in layouts) or 1
    cell_height = grid_height / max_row_end

    palette = ["#2563eb", "#7c3aed", "#0891b2", "#059669", "#d97706", "#dc2626"]
    for index, widget in enumerate(widgets[:12]):
        col, row, size_x, size_y = layouts[index]
        x = PADDING + col * cell_width + 3
        y = grid_top + row * cell_height + 3
        w = size_x * cell_width - 6
        h = size_y * cell_height - 6
        color = palette[index % len(palette)]
        label = widget.visualization.name if widget.visualization else (widget.text or "Text")[:20]
        lines.append(f'<rect x="{x:.1f}" y="{y:.1f}" width="{w:.1f}" height="{h:.1f}" fill="{color}22" stroke="{color}" rx="5"/>')
        if h >= 22:
            lines.append(
                f'<text x="{x + 6:.1f}" y="{y + 14:.1f}" fill="{TEXT}" font-family="Inter, Arial, sans-serif" font-size="10" font-weight="600">{_escape(label)}</text>'
            )
        if widget.visualization and h >= 34:
            lines.append(
                f'<text x="{x + 6:.1f}" y="{y + 28:.1f}" fill="{MUTED}" font-family="Inter, Arial, sans-serif" font-size="9">{_escape(widget.visualization.type)}</text>'
            )

    return _svg_close(lines)
