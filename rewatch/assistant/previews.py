"""SVG preview images for assistant chat illustrations."""

from __future__ import annotations

import html
import math
from typing import Any, Optional

from rewatch import models
from rewatch.assistant.dashboard_layout import widget_position
from rewatch.permissions import has_access, view_only

WIDTH = 520
HEIGHT = 300
PADDING = 16
BG = "#f8fafc"
TEXT = "#1e293b"
MUTED = "#64748b"
ACCENT = "#2563eb"
GRID = "#e2e8f0"
CARD = "#ffffff"

_PREVIEW_PALETTES = {
    "light": {
        "bg": "#f5f2ec",
        "text": "#1f1a16",
        "muted": "#7a7068",
        "grid": "#ece8e1",
        "card": "#ffffff",
        "accent": "#ff7230",
    },
    "dark": {
        "bg": "#15110d",
        "text": "#f3eee8",
        "muted": "#a59c91",
        "grid": "#2e2620",
        "card": "#1f1a16",
        "accent": "#ff7230",
    },
}


def get_preview_palette(theme: Optional[str] = None) -> dict[str, str]:
    if theme == "dark":
        return _PREVIEW_PALETTES["dark"]
    return _PREVIEW_PALETTES["light"]


def preview_path(base_url: str, resource: str, resource_id: int | str) -> str:
    base = base_url.rstrip("/")
    return f"{base}/api/assistant/previews/{resource}/{resource_id}"


def _escape(value: Any) -> str:
    return html.escape(str(value if value is not None else ""))


def _escape_trunc(value: Any, limit: int) -> str:
    """Truncate before escaping so entities are never cut in half."""
    return html.escape(str(value if value is not None else "")[:limit])


def _safe_int(value: Any, default: int = 1) -> int:
    """Tolerant int coercion for LLM/user-supplied option values."""
    try:
        return int(float(value))
    except (TypeError, ValueError):
        return default


def _query_rows(query: models.Query) -> tuple[list[str], list[dict[str, Any]]]:
    result = query.latest_query_data
    if not result or not result.data:
        return [], []
    columns = [col.get("name", "") for col in result.data.get("columns", [])]
    rows = result.data.get("rows", []) or []
    return columns, rows


def _svg_open(title: str, subtitle: Optional[str] = None, colors: Optional[dict[str, str]] = None) -> list[str]:
    palette = colors or {"bg": BG, "text": TEXT, "muted": MUTED}
    lines = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{WIDTH}" height="{HEIGHT}" viewBox="0 0 {WIDTH} {HEIGHT}">',
        f'<rect width="100%" height="100%" fill="{palette["bg"]}" rx="12"/>',
        f'<text x="{PADDING}" y="28" fill="{palette["text"]}" font-family="Inter, Arial, sans-serif" font-size="15" font-weight="600">{_escape(title)}</text>',
    ]
    if subtitle:
        lines.append(
            f'<text x="{PADDING}" y="48" fill="{palette["muted"]}" font-family="Inter, Arial, sans-serif" font-size="12">{_escape(subtitle)}</text>'
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
                f'<text x="{x + 8}" y="{y + 16}" fill="{TEXT}" font-family="Inter, Arial, sans-serif" font-size="11">{_escape_trunc(value, 22)}</text>'
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
    labels = [_escape_trunc(row.get(x_col, ""), 10) for row in points]
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
    row_index = max(_safe_int(opts.get("rowNumber"), 1) - 1, 0)
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


def _cell_font_size(height: float, scale: float = 0.18, minimum: int = 6, maximum: int = 11) -> int:
    return max(minimum, min(maximum, int(height * scale)))


def _render_cell_placeholder(
    width: float,
    height: float,
    colors: dict[str, str],
    label: str,
    subtitle: Optional[str] = None,
) -> list[str]:
    accent = colors.get("accent", ACCENT)
    lines = [
        f'<rect x="0" y="0" width="{width:.1f}" height="{height:.1f}" fill="{accent}18"/>',
    ]
    if height < 14 or width < 16:
        return lines

    font_size = _cell_font_size(height)
    lines.append(
        f'<text x="{width / 2:.1f}" y="{height / 2 - (5 if subtitle else 0):.1f}" fill="{colors["text"]}" '
        f'font-family="Inter, Arial, sans-serif" font-size="{font_size}" font-weight="600" text-anchor="middle">'
        f"{_escape(label[: max(4, int(width / 5))])}</text>"
    )
    if subtitle and height >= 28:
        lines.append(
            f'<text x="{width / 2:.1f}" y="{height / 2 + 12:.1f}" fill="{colors["muted"]}" '
            f'font-family="Inter, Arial, sans-serif" font-size="{max(6, font_size - 1)}" text-anchor="middle">'
            f"{_escape(subtitle)}</text>"
        )
    return lines


def _render_cell_textbox(text: str, width: float, height: float, colors: dict[str, str]) -> list[str]:
    font_size = _cell_font_size(height, scale=0.16, minimum=7, maximum=10)
    line_height = font_size + 2
    max_lines = max(1, int((height - 6) / line_height))
    chars_per_line = max(8, int(width / (font_size * 0.55)))
    lines = []
    y = 4 + font_size
    rendered = 0
    for raw_line in (text or "").splitlines() or [""]:
        if rendered >= max_lines:
            break
        snippet = raw_line[:chars_per_line]
        lines.append(
            f'<text x="4" y="{y:.1f}" fill="{colors["text"]}" font-family="Inter, Arial, sans-serif" font-size="{font_size}">'
            f"{_escape(snippet)}</text>"
        )
        y += line_height
        rendered += 1
    return lines


def _render_cell_counter(
    columns: list[str],
    rows: list[dict[str, Any]],
    options: dict[str, Any],
    width: float,
    height: float,
    colors: dict[str, str],
) -> list[str]:
    opts = options or {}
    column = opts.get("counterColName") or (columns[0] if columns else None)
    row_index = max(_safe_int(opts.get("rowNumber"), 1) - 1, 0)
    row = rows[min(row_index, len(rows) - 1)] if rows else {}
    value = row.get(column, "") if column else ""
    accent = colors.get("accent", ACCENT)
    value_size = _cell_font_size(height, scale=0.34, minimum=10, maximum=24)
    label_size = max(6, value_size - 4)
    lines = [
        f'<text x="{width / 2:.1f}" y="{height / 2 + 2:.1f}" fill="{accent}" font-family="Inter, Arial, sans-serif" '
        f'font-size="{value_size}" font-weight="700" text-anchor="middle">{_escape(value)}</text>'
    ]
    if height >= 28:
        label = opts.get("counterLabel") or column or ""
        lines.append(
            f'<text x="{width / 2:.1f}" y="{min(height - 4, height / 2 + value_size):.1f}" fill="{colors["muted"]}" '
            f'font-family="Inter, Arial, sans-serif" font-size="{label_size}" text-anchor="middle">'
            f"{_escape(label[: max(4, int(width / 6))])}</text>"
        )
    return lines


def _render_cell_table(
    columns: list[str],
    rows: list[dict[str, Any]],
    width: float,
    height: float,
    colors: dict[str, str],
) -> list[str]:
    if not columns:
        return _render_cell_placeholder(width, height, colors, "Table", "No data")

    display_cols = columns[: min(3, max(1, int(width / 36)))]
    row_height = max(8, min(12, int(height / 5)))
    header_height = row_height if height >= 24 else 0
    max_rows = max(1, int((height - header_height - 4) / row_height))
    display_rows = rows[:max_rows]
    col_width = width / max(len(display_cols), 1)
    font_size = max(6, min(9, row_height - 3))
    lines = []

    if header_height:
        for index, column in enumerate(display_cols):
            x = index * col_width
            lines.append(
                f'<rect x="{x:.1f}" y="0" width="{col_width - 1:.1f}" height="{header_height:.1f}" fill="{colors["grid"]}"/>'
            )
            lines.append(
                f'<text x="{x + 3:.1f}" y="{header_height - 3:.1f}" fill="{colors["text"]}" '
                f'font-family="Inter, Arial, sans-serif" font-size="{font_size}" font-weight="600">'
                f"{_escape(column[: max(3, int(col_width / 5))])}</text>"
            )

    for row_index, row in enumerate(display_rows):
        y = header_height + row_index * row_height
        fill = colors["card"] if row_index % 2 == 0 else colors["bg"]
        for col_index, column in enumerate(display_cols):
            x = col_index * col_width
            lines.append(
                f'<rect x="{x:.1f}" y="{y:.1f}" width="{col_width - 1:.1f}" height="{row_height:.1f}" '
                f'fill="{fill}" stroke="{colors["grid"]}"/>'
            )
            value = row.get(column, "")
            lines.append(
                f'<text x="{x + 3:.1f}" y="{y + row_height - 3:.1f}" fill="{colors["text"]}" '
                f'font-family="Inter, Arial, sans-serif" font-size="{font_size}">'
                f"{_escape_trunc(value, max(3, int(col_width / 5)))}</text>"
            )
    return lines


def _chart_values(columns: list[str], rows: list[dict[str, Any]], options: dict[str, Any]) -> tuple[Optional[str], Optional[str], list[float]]:
    x_col, y_cols = _chart_columns(options or {}, columns)
    y_col = y_cols[0] if y_cols else None
    if not x_col or not y_col:
        return None, None, []
    values: list[float] = []
    for row in rows[:8]:
        raw = row.get(y_col, 0)
        try:
            values.append(float(raw))
        except (TypeError, ValueError):
            values.append(0.0)
    return x_col, y_col, values


def _render_cell_chart(
    columns: list[str],
    rows: list[dict[str, Any]],
    options: dict[str, Any],
    width: float,
    height: float,
    colors: dict[str, str],
) -> list[str]:
    _, _, values = _chart_values(columns, rows, options or {})
    if not values:
        return _render_cell_table(columns, rows, width, height, colors)

    accent = colors.get("accent", ACCENT)
    series_type = (options or {}).get("globalSeriesType") or "column"
    top = 4
    chart_height = max(8.0, height - top - 4)
    chart_width = max(8.0, width - 8)
    lines = []

    if series_type in ("line", "area", "scatter") and len(values) >= 2:
        max_value = max(values) or 1.0
        coords = []
        step = chart_width / max(len(values) - 1, 1)
        for index, value in enumerate(values):
            x = 4 + index * step
            y = top + chart_height - (value / max_value) * (chart_height - 2) - 1
            coords.append((x, y))
        path = "M " + " L ".join(f"{x:.1f} {y:.1f}" for x, y in coords)
        if series_type == "area" and len(coords) >= 2:
            base_y = top + chart_height - 1
            area_path = f"{path} L {coords[-1][0]:.1f} {base_y:.1f} L {coords[0][0]:.1f} {base_y:.1f} Z"
            lines.append(f'<path d="{area_path}" fill="{accent}33" stroke="none"/>')
        lines.append(f'<path d="{path}" fill="none" stroke="{accent}" stroke-width="1.5"/>')
        return lines

    if series_type == "pie" and min(width, height) >= 28:
        total = sum(abs(value) for value in values) or 1.0
        cx = width / 2
        cy = top + chart_height / 2
        radius = min(chart_width, chart_height) / 2 - 2
        start = -math.pi / 2
        pie_palette = ["#2563eb", "#7c3aed", "#0891b2", "#059669", "#d97706", accent]
        for index, value in enumerate(values[:6]):
            angle = (abs(value) / total) * math.pi * 2
            end = start + angle
            x1 = cx + radius * math.cos(start)
            y1 = cy + radius * math.sin(start)
            x2 = cx + radius * math.cos(end)
            y2 = cy + radius * math.sin(end)
            large = 1 if angle > math.pi else 0
            color = pie_palette[index % len(pie_palette)]
            lines.append(
                f'<path d="M {cx:.1f} {cy:.1f} L {x1:.1f} {y1:.1f} A {radius:.1f} {radius:.1f} 0 {large} 1 {x2:.1f} {y2:.1f} Z" fill="{color}"/>'
            )
            start = end
        return lines

    max_value = max(values) or 1.0
    bar_gap = 2.0
    bar_width = max(3.0, (chart_width - bar_gap * (len(values) + 1)) / max(len(values), 1))
    for index, value in enumerate(values):
        x = 4 + bar_gap + index * (bar_width + bar_gap)
        bar_height = (value / max_value) * (chart_height - 2)
        y = top + chart_height - bar_height - 1
        lines.append(f'<rect x="{x:.1f}" y="{y:.1f}" width="{bar_width:.1f}" height="{bar_height:.1f}" fill="{accent}" rx="1"/>')
    return lines


def _render_widget_cell_content(
    widget: models.Widget,
    width: float,
    height: float,
    colors: dict[str, str],
    user: Optional[models.User] = None,
) -> list[str]:
    visualization = widget.visualization
    if visualization is not None:
        query = visualization.query_rel
        label = visualization.name or visualization.type or "Chart"
        if query is None or (user is not None and not has_access(query, user, view_only)):
            return _render_cell_placeholder(width, height, colors, label, "Restricted")
        columns, rows = _query_rows(query)
        if not rows:
            return _render_cell_placeholder(width, height, colors, label, "No data")
        options = visualization.options or {}
        viz_type = (visualization.type or "TABLE").upper()
        if viz_type == "CHART":
            return _render_cell_chart(columns, rows, options, width, height, colors)
        if viz_type == "COUNTER":
            return _render_cell_counter(columns, rows, options, width, height, colors)
        return _render_cell_table(columns, rows, width, height, colors)

    if widget.text:
        return _render_cell_textbox(widget.text, width, height, colors)

    return _render_cell_placeholder(width, height, colors, "Widget")


def render_dashboard_svg(
    dashboard: models.Dashboard,
    theme: Optional[str] = None,
    widgets: Optional[list[models.Widget]] = None,
    user: Optional[models.User] = None,
) -> str:
    colors = get_preview_palette(theme)
    widgets = widgets if widgets is not None else list(dashboard.widgets)
    lines = _svg_open(dashboard.name or f"Dashboard {dashboard.id}", f"{len(widgets)} widgets", colors=colors)
    grid_cols = 12
    grid_top = 62
    grid_height = HEIGHT - grid_top - 16
    cell_width = (WIDTH - PADDING * 2) / grid_cols

    lines.append(
        f'<rect x="{PADDING}" y="{grid_top}" width="{WIDTH - PADDING * 2}" height="{grid_height}" fill="{colors["card"]}" stroke="{colors["grid"]}" rx="8"/>'
    )

    if not widgets:
        lines.append(
            f'<text x="{WIDTH / 2}" y="{grid_top + grid_height / 2}" fill="{colors["muted"]}" font-family="Inter, Arial, sans-serif" font-size="13" text-anchor="middle">No widgets yet</text>'
        )
        return _svg_close(lines)

    visible_widgets = widgets[:12]
    layouts = [_widget_layout(widget) for widget in visible_widgets]
    max_row_end = max(row + size_y for _, row, _, size_y in layouts) or 1
    cell_height = grid_height / max_row_end

    clip_defs: list[str] = []
    for index, widget in enumerate(visible_widgets):
        col, row, size_x, size_y = layouts[index]
        x = PADDING + col * cell_width + 3
        y = grid_top + row * cell_height + 3
        w = max(12.0, size_x * cell_width - 6)
        h = max(12.0, size_y * cell_height - 6)
        clip_id = f"widget-clip-{index}"
        clip_defs.append(
            f'<clipPath id="{clip_id}"><rect x="{x:.1f}" y="{y:.1f}" width="{w:.1f}" height="{h:.1f}" rx="5"/></clipPath>'
        )

    if clip_defs:
        lines.append("<defs>" + "".join(clip_defs) + "</defs>")

    for index, widget in enumerate(visible_widgets):
        col, row, size_x, size_y = layouts[index]
        x = PADDING + col * cell_width + 3
        y = grid_top + row * cell_height + 3
        w = max(12.0, size_x * cell_width - 6)
        h = max(12.0, size_y * cell_height - 6)
        clip_id = f"widget-clip-{index}"
        lines.append(f'<g clip-path="url(#{clip_id})">')
        lines.append(
            f'<rect x="{x:.1f}" y="{y:.1f}" width="{w:.1f}" height="{h:.1f}" fill="{colors["card"]}" stroke="{colors["grid"]}" rx="5"/>'
        )
        lines.append(f'<g transform="translate({x:.1f},{y:.1f})">')
        lines.extend(_render_widget_cell_content(widget, w, h, colors, user=user))
        lines.append("</g>")
        lines.append("</g>")

    return _svg_close(lines)
