from types import SimpleNamespace

from rewatch.assistant.previews import (
    _render_cell_chart,
    _render_cell_counter,
    _render_cell_table,
    _render_cell_textbox,
    _render_widget_cell_content,
    get_preview_palette,
    render_dashboard_svg,
)


def _widget(*, text=None, visualization=None):
    return SimpleNamespace(text=text, visualization=visualization, options={"position": {"col": 0, "row": 0, "sizeX": 6, "sizeY": 3}})


def _visualization(*, viz_type="CHART", name="Revenue", columns=None, rows=None, options=None):
    data = None
    if columns is not None:
        data = {"columns": [{"name": column} for column in columns], "rows": rows or []}
    query = SimpleNamespace(latest_query_data=SimpleNamespace(data=data) if data is not None else None)
    return SimpleNamespace(
        name=name,
        type=viz_type,
        options=options or {},
        query_rel=query,
    )


def test_render_cell_textbox_shows_content():
    lines = _render_cell_textbox("Hello dashboard", 120, 60, get_preview_palette("light"))
    svg = "\n".join(lines)
    assert "Hello dashboard" in svg


def test_render_cell_chart_draws_bars_from_cached_data():
    lines = _render_cell_chart(
        ["month", "total"],
        [{"month": "Jan", "total": 10}, {"month": "Feb", "total": 20}],
        {"globalSeriesType": "column", "columnMapping": {"month": "x", "total": "y"}},
        120,
        60,
        get_preview_palette("light"),
    )
    svg = "\n".join(lines)
    assert "<rect" in svg


def test_render_cell_counter_shows_value():
    lines = _render_cell_counter(
        ["total"],
        [{"total": 42}],
        {"counterColName": "total"},
        120,
        60,
        get_preview_palette("dark"),
    )
    svg = "\n".join(lines)
    assert "42" in svg


def test_render_cell_table_renders_rows():
    lines = _render_cell_table(
        ["name", "value"],
        [{"name": "alpha", "value": 1}, {"name": "beta", "value": 2}],
        140,
        70,
        get_preview_palette("light"),
    )
    svg = "\n".join(lines)
    assert "alpha" in svg
    assert "beta" in svg


def test_render_widget_cell_content_uses_visualization_data():
    widget = _widget(visualization=_visualization(columns=["month", "total"], rows=[{"month": "Jan", "total": 3}]))
    lines = _render_widget_cell_content(widget, 120, 60, get_preview_palette("light"))
    svg = "\n".join(lines)
    assert "<rect" in svg


def test_render_dashboard_svg_composites_widgets():
    dashboard = SimpleNamespace(id=7, name="Ops", widgets=[])
    widgets = [
        _widget(
            visualization=_visualization(
                columns=["metric", "value"],
                rows=[{"metric": "Users", "value": 99}],
                options={"globalSeriesType": "column", "columnMapping": {"metric": "x", "value": "y"}},
            )
        ),
        _widget(text="Status: healthy"),
    ]
    svg = render_dashboard_svg(dashboard, theme="dark", widgets=widgets)
    assert "Ops" in svg
    assert "Status: healthy" in svg
    assert "widget-clip-0" in svg
