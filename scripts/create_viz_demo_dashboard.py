#!/usr/bin/env python3
"""Create a dashboard with queries and visualizations to exercise all chart types."""

from __future__ import annotations

import json
import os
import sys
import urllib.error
import urllib.request

BASE_URL = os.environ.get("REWATCH_BASE_URL", "https://rewatch.naoufel.io").rstrip("/")
API_KEY = os.environ.get("REWATCH_API_KEY", "")
DATA_SOURCE_ID = int(os.environ.get("VIZ_DEMO_DATA_SOURCE_ID", "2"))

DASHBOARD_NAME = "Visualization Gallery (ECharts + Nivo)"


def api(method: str, path: str, body: dict | None = None) -> dict:
    url = f"{BASE_URL}{path}"
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(
        url,
        data=data,
        method=method,
        headers={
            "Authorization": f"Key {API_KEY}",
            "Content-Type": "application/json",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=120) as resp:
            raw = resp.read().decode()
            return json.loads(raw) if raw else {}
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode()
        raise RuntimeError(f"{method} {path} -> {exc.code}: {detail}") from exc


def chart_viz(name: str, series_type: str, column_mapping: dict, *, x_axis_type: str | None = None) -> dict:
    options: dict = {
        "globalSeriesType": series_type,
        "columnMapping": column_mapping,
        "legend": {"enabled": True},
        "sortX": True,
    }
    if x_axis_type:
        options["xAxis"] = {"type": x_axis_type, "labels": {"enabled": True}}
    return {
        "type": "CHART",
        "name": name,
        "options": options,
    }


def widget_position(col: int, row: int, size_x: int = 6, size_y: int = 8) -> dict:
    return {
        "position": {
            "col": col,
            "row": row,
            "sizeX": size_x,
            "sizeY": size_y,
            "minSizeX": 2,
            "maxSizeX": 12,
            "minSizeY": 2,
            "maxSizeY": 1000,
            "autoHeight": False,
        }
    }


QUERIES = [
    {
        "name": "Viz Demo – Time Series",
        "description": "Multi-series time data for line, area, bar, and theme river charts.",
        "query": """
SELECT d::date AS date, s AS series, v AS value
FROM (VALUES
  ('2024-01-01','Alpha',10),('2024-02-01','Alpha',14),('2024-03-01','Alpha',18),('2024-04-01','Alpha',16),('2024-05-01','Alpha',20),
  ('2024-01-01','Beta',8),('2024-02-01','Beta',11),('2024-03-01','Beta',15),('2024-04-01','Beta',13),('2024-05-01','Beta',17)
) AS t(d, s, v)
ORDER BY 1, 2
""".strip(),
        "visualizations": [
            chart_viz("Line", "line", {"date": "x", "value": "y", "series": "series"}, x_axis_type="datetime"),
            chart_viz("Area", "area", {"date": "x", "value": "y", "series": "series"}, x_axis_type="datetime"),
            chart_viz("Bar", "column", {"date": "x", "value": "y", "series": "series"}, x_axis_type="datetime"),
            chart_viz("Theme River", "themeRiver", {"date": "x", "value": "y", "series": "series"}, x_axis_type="datetime"),
        ],
    },
    {
        "name": "Viz Demo – Categories",
        "description": "Category totals for pie, bar, pictorial bar, and treemap.",
        "query": """
SELECT category, value FROM (VALUES
  ('Apple',45),('Banana',32),('Cherry',28),('Date',15),('Elderberry',9),('Fig',22)
) AS t(category, value)
ORDER BY value DESC
""".strip(),
        "visualizations": [
            chart_viz("Pie", "pie", {"category": "x", "value": "y"}, x_axis_type="category"),
            chart_viz("Column", "column", {"category": "x", "value": "y"}, x_axis_type="category"),
            chart_viz("Pictorial Bar", "pictorialBar", {"category": "x", "value": "y"}, x_axis_type="category"),
            chart_viz("Treemap", "treemap", {"category": "x", "value": "y"}, x_axis_type="category"),
        ],
    },
    {
        "name": "Viz Demo – Scatter",
        "description": "XY data with bubble sizes.",
        "query": """
SELECT x_val, y_val, size_val FROM (VALUES
  (1,2,10),(2,5,20),(3,3,15),(4,8,30),(5,6,25),(6,9,35),(7,4,18),(8,7,28),(9,5,22),(10,8,32)
) AS t(x_val, y_val, size_val)
""".strip(),
        "visualizations": [
            chart_viz("Scatter", "scatter", {"x_val": "x", "y_val": "y"}),
            chart_viz("Effect Scatter", "effectScatter", {"x_val": "x", "y_val": "y"}),
            chart_viz("Bubble", "bubble", {"x_val": "x", "y_val": "y", "size_val": "size"}),
        ],
    },
    {
        "name": "Viz Demo – Heatmap",
        "description": "Grid intensity data.",
        "query": """
SELECT x_cat, y_cat, intensity FROM (VALUES
  ('Mon','Team A',5),('Tue','Team A',8),('Wed','Team A',3),('Thu','Team A',9),('Fri','Team A',6),
  ('Mon','Team B',7),('Tue','Team B',4),('Wed','Team B',6),('Thu','Team B',2),('Fri','Team B',8),
  ('Mon','Team C',3),('Tue','Team C',9),('Wed','Team C',5),('Thu','Team C',7),('Fri','Team C',4)
) AS t(x_cat, y_cat, intensity)
""".strip(),
        "visualizations": [
            chart_viz("Heatmap", "heatmap", {"x_cat": "x", "y_cat": "y", "intensity": "zVal"}),
        ],
    },
    {
        "name": "Viz Demo – Distribution",
        "description": "Grouped measurements for box plots.",
        "query": """
SELECT group_name, measurement FROM (VALUES
  ('Group A',10),('Group A',12),('Group A',14),('Group A',11),('Group A',13),('Group A',9),
  ('Group B',20),('Group B',22),('Group B',18),('Group B',25),('Group B',21),('Group B',19),
  ('Group C',5),('Group C',7),('Group C',6),('Group C',8),('Group C',4),('Group C',6)
) AS t(group_name, measurement)
""".strip(),
        "visualizations": [
            chart_viz("Box (Chart)", "box", {"group_name": "x", "measurement": "y"}),
            {"type": "BOXPLOT", "name": "Box Plot", "options": {}},
        ],
    },
    {
        "name": "Viz Demo – OHLC",
        "description": "Candlestick sample prices.",
        "query": """
SELECT d::date AS date, o AS open, h AS high, l AS low, c AS close FROM (VALUES
  ('2024-01-01',100,110,95,105),('2024-01-02',105,112,102,108),('2024-01-03',108,115,106,110),
  ('2024-01-04',110,118,108,112),('2024-01-05',112,120,109,115),('2024-01-08',115,122,113,118),
  ('2024-01-09',118,125,116,120),('2024-01-10',120,128,118,122)
) AS t(d, o, h, l, c)
ORDER BY 1
""".strip(),
        "visualizations": [
            chart_viz(
                "Candlestick",
                "candlestick",
                {"date": "x", "open": "open", "high": "high", "low": "low", "close": "close"},
            ),
        ],
    },
    {
        "name": "Viz Demo – Radar",
        "description": "Team scores across metrics.",
        "query": """
SELECT metric, team, score FROM (VALUES
  ('Speed','Team A',80),('Power','Team A',90),('Range','Team A',70),('Defense','Team A',85),('Agility','Team A',75),
  ('Speed','Team B',65),('Power','Team B',75),('Range','Team B',95),('Defense','Team B',60),('Agility','Team B',88)
) AS t(metric, team, score)
""".strip(),
        "visualizations": [
            chart_viz("Radar", "radar", {"metric": "x", "score": "y", "team": "series"}),
        ],
    },
    {
        "name": "Viz Demo – KPI",
        "description": "Single metric for gauge and counter.",
        "query": "SELECT 73 AS completion_pct",
        "visualizations": [
            chart_viz("Gauge", "gauge", {"completion_pct": "y"}),
            {
                "type": "COUNTER",
                "name": "Counter",
                "options": {
                    "counterColName": "completion_pct",
                    "counterLabel": "Completion %",
                    "rowNumber": 1,
                    "targetRowNumber": 1,
                },
            },
        ],
    },
    {
        "name": "Viz Demo – Parallel",
        "description": "Multi-dimensional rows for parallel coordinates.",
        "query": """
SELECT dim1, dim2, dim3, dim4 FROM (VALUES
  (80,90,70,85),(60,75,95,65),(90,80,60,75),(70,85,80,90),(55,65,88,72)
) AS t(dim1, dim2, dim3, dim4)
""".strip(),
        "visualizations": [
            chart_viz("Parallel", "parallel", {"dim1": "y", "dim2": "y", "dim3": "y", "dim4": "y"}),
        ],
    },
    {
        "name": "Viz Demo – Flow",
        "description": "Stage sequences for sankey and sunburst.",
        "query": """
SELECT s1, s2, s3, s4, s5, value FROM (VALUES
  ('Visit','Signup','Trial','Purchase',NULL,800),
  ('Visit','Signup','Trial','Churn',NULL,250),
  ('Visit','Signup',NULL,NULL,NULL,150),
  ('Visit','Bounce',NULL,NULL,NULL,400),
  ('Referral','Signup','Trial','Purchase',NULL,120)
) AS t(s1, s2, s3, s4, s5, value)
""".strip(),
        "visualizations": [
            {"type": "SANKEY", "name": "Sankey", "options": {}},
            {"type": "SUNBURST_SEQUENCE", "name": "Sunburst", "options": {}},
        ],
    },
    {
        "name": "Viz Demo – Funnel",
        "description": "Conversion funnel steps.",
        "query": """
SELECT step, value FROM (VALUES
  ('Visit',10000),('Signup',4200),('Trial',2100),('Purchase',850),('Renewal',620)
) AS t(step, value)
ORDER BY value DESC
""".strip(),
        "visualizations": [
            {
                "type": "FUNNEL",
                "name": "Funnel",
                "options": {
                    "stepCol": {"colName": "step", "displayAs": "Step"},
                    "valueCol": {"colName": "value", "displayAs": "Users"},
                },
            },
        ],
    },
    {
        "name": "Viz Demo – Word Cloud",
        "description": "Token frequencies.",
        "query": """
SELECT word, count FROM (VALUES
  ('ethereum',120),('bitcoin',95),('defi',80),('nft',60),('dao',45),
  ('layer2',40),('staking',35),('rollup',30),('wallet',28),('solidity',22)
) AS t(word, count)
""".strip(),
        "visualizations": [
            {
                "type": "WORD_CLOUD",
                "name": "Word Cloud",
                "options": {"column": "word", "frequenciesColumn": "count"},
            },
        ],
    },
    {
        "name": "Viz Demo – Choropleth",
        "description": "Country-level values.",
        "query": """
SELECT country_code, gdp FROM (VALUES
  ('US',21000),('FR',2700),('DE',3800),('GB',2800),('JP',4200),
  ('CN',14000),('IN',3300),('BR',1800),('CA',1900),('AU',1600)
) AS t(country_code, gdp)
""".strip(),
        "visualizations": [
            {
                "type": "CHOROPLETH",
                "name": "Choropleth",
                "options": {
                    "mapType": "countries",
                    "keyColumn": "country_code",
                    "targetField": "iso_a2",
                    "valueColumn": "gdp",
                },
            },
        ],
    },
]


def main() -> int:
    if not API_KEY:
        print("Set REWATCH_API_KEY", file=sys.stderr)
        return 1

    print(f"Creating dashboard on {BASE_URL} ...")
    dashboard = api("POST", "/api/dashboards", {"name": DASHBOARD_NAME})
    dashboard_id = dashboard["id"]
    print(f"  Dashboard id={dashboard_id}")

    widgets_to_add: list[tuple[int, dict]] = []
    size_x, size_y = 6, 8
    start_row = 3  # below intro text widget

    for spec in QUERIES:
        print(f"  Query: {spec['name']}")
        query = api(
            "POST",
            "/api/queries",
            {
                "name": spec["name"],
                "description": spec.get("description"),
                "query": spec["query"],
                "data_source_id": DATA_SOURCE_ID,
                "is_draft": False,
            },
        )
        query_id = query["id"]
        # Execute once so latest_query_data is populated
        api("POST", f"/api/queries/{query_id}/refresh")

        for viz_spec in spec["visualizations"]:
            viz = api(
                "POST",
                "/api/visualizations",
                {
                    "query_id": query_id,
                    "type": viz_spec["type"],
                    "name": viz_spec["name"],
                    "options": viz_spec.get("options", {}),
                },
            )
            widget_idx = len(widgets_to_add)
            col = 0 if widget_idx % 2 == 0 else size_x
            row = start_row + (widget_idx // 2) * size_y
            widgets_to_add.append((viz["id"], widget_position(col, row, size_x, size_y)))
            print(f"    + {viz_spec['type']}: {viz_spec['name']} (viz {viz['id']})")

    # Intro text widget at top
    intro = api(
        "POST",
        "/api/widgets",
        {
            "dashboard_id": dashboard_id,
            "visualization_id": None,
            "text": (
                "# Visualization Gallery\n\n"
                "Smoke-test dashboard for **ECharts** chart types and **Nivo/ECharts** satellite visualizations "
                "after the Plotly migration. Each widget uses synthetic SQL data from the Inverse Postgres source."
            ),
            "options": widget_position(0, 0, 12, 3),
            "width": 1,
        },
    )
    print(f"  Text widget id={intro['id']}")

    # Add visualization widgets (positions already include start_row offset)
    for viz_id, opts in widgets_to_add:
        api(
            "POST",
            "/api/widgets",
            {
                "dashboard_id": dashboard_id,
                "visualization_id": viz_id,
                "options": opts,
                "width": 1,
            },
        )

    api("POST", f"/api/dashboards/{dashboard_id}", {"is_draft": False, "name": DASHBOARD_NAME})
    slug = dashboard.get("slug") or dashboard_id
    print(f"\nDone. Dashboard: {BASE_URL}/dashboards/{dashboard_id}-{slug}")
    print(f"  {len(widgets_to_add)} visualization widgets + 1 text header")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
