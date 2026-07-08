---
name: rewatch-visualizations-dashboards
description: Creates and configures Rewatch visualizations (charts, counters, maps, tables) and publishes them on dashboards via MCP/API. Use when building charts, KPIs, maps, dashboard widgets, or arranging dashboard layouts in Rewatch.
---

# Rewatch Visualizations & Dashboards

## Quick start

**Full dashboard (3+ widgets)? Use `build_dashboard_from_spec` — one call does everything.**

```
run_query (explore columns) → build_dashboard_from_spec(name, queries, widgets, derived?)
```

Incremental flow (single viz, edits to existing dashboards):

```
run_query → create_query → create_visualization → create_dashboard → add_widget_to_dashboard → update_dashboard(is_draft=false)
```

Use the **user-rewatch** MCP server. Prefer dedicated tools over `call_api`.

## Fast path: build_dashboard_from_spec

One call validates every query (nothing is created if any fails), creates queries + visualizations + widgets, computes the grid layout, and publishes.

```json
{
  "name": "Ethereum DeFi Ecosystem",
  "queries": [
    {
      "key": "protocols",
      "name": "DeFi - All Protocols",
      "data_source_id": 10,
      "query": "endpoint: protocols",
      "visualizations": []
    },
    {
      "name": "DeFi - ETH TVL History",
      "data_source_id": 10,
      "query": "endpoint: historical-chain-tvl-chain\nchain: Ethereum",
      "visualizations": [
        {"type": "CHART", "name": "ETH TVL", "chart_type": "area",
         "column_mapping": {"datetime": "x", "tvl": "y"}}
      ]
    }
  ],
  "derived": [
    {
      "name": "DeFi - Top Protocols",
      "query": "SELECT name, category, ROUND(chainTvls_Ethereum / 1e9, 2) AS eth_tvl_b\nFROM {{cached_query.protocols}}\nWHERE chainTvls_Ethereum > 1e6\nORDER BY chainTvls_Ethereum DESC LIMIT 20",
      "visualizations": [{"type": "TABLE", "name": "Top Protocols"}]
    }
  ],
  "widgets": [
    {"text": "# Ethereum DeFi\n\nTVL and protocol landscape."},
    {"text": "## TVL"},
    {"visualization": "ETH TVL", "role": "full"},
    {"visualization": "Top Protocols"}
  ]
}
```

Key rules:

- **Base query `key`** lets `derived` queries reference its cached results as `{{cached_query.KEY}}`. The builder creates base queries, refreshes them, substitutes real `cached_query_{id}` table names, then creates the derived queries on the Query Results source.
- **Derived SQL runs on SQLite** — no PostgreSQL casts (`::numeric`, `COUNT(*)::int`). Use `ROUND(x, 2)`, `CAST(x AS INTEGER)`.
- **Widgets auto-layout** with type-aware sizes: counters 3×8 packed 4 per row, charts 6×8 side by side, tables 12×8, text headers full width. Override with `role` (`title`, `section`, `kpi`, `half`, `third`, `full`) or explicit `position`.
- Widget `visualization` references the viz **name** from the spec — names must be unique.
- Queries and the dashboard are **published automatically** (pass `publish: false` for a draft).

Related composite tools:

- `create_multi_visualization_query(name, query, data_source_id, visualizations)` — one wide summary row rendered as several KPI counters, without a full dashboard.
- `refresh_queries_and_wait(query_ids)` — refresh + wait for cached results before manually creating `cached_query_{id}` queries.

## Core workflow (incremental)

### 1. Validate query data first

Always inspect columns and sample rows before creating visualizations.

```text
run_query(query_text=..., data_source_id=...)   # ad-hoc
run_query(query_id=...)                          # saved query
```

Read `columns`, `rows`, and any `visualization_hints` in the response. **Never invent column names** — they must match query results exactly (case-sensitive, dots allowed, e.g. `market_cap.usd`).

If no data source is specified, call `list_data_sources` and pick the best match.

### 2. Save the query (if needed)

```text
create_query(name, query, data_source_id, description?)
update_query(query_id, is_draft=false)   # publish when ready
```

New queries get a default **TABLE** visualization automatically. Refresh once so `latest_query_data` is populated:

```text
refresh_queries_and_wait(query_ids=[query_id])
```

### 3. Choose visualization type

Browse types when unsure:

```text
list_visualization_types
get_visualization_type(type="CHART")   # required/common options + dashboard_workflow
```

| Goal | Type | Notes |
|------|------|-------|
| Tabular data | `TABLE` | Default; shows all columns |
| Time series / categories | `CHART` | ECharts: line, column, bar, area, pie, scatter, … |
| Single KPI | `COUNTER` | One numeric value from one row |
| Lat/lon points | `MAP` | Needs numeric lat + lon columns |
| Region aggregates | `CHOROPLETH` | Country/state codes + metric |
| Funnel steps | `FUNNEL` | step + value columns |
| Flows | `SANKEY` | source → target → weight |
| Distributions | `BOXPLOT` | grouped measurements |
| Text frequency | `WORD_CLOUD` | word + count columns |

See [reference.md](reference.md) for chart series types and option examples.

### 4. Create the visualization

```text
create_visualization(query_id, type, name, options?, description?)
```

**Critical rule — omit options for CHART and COUNTER unless the user asks for a specific style.** The server auto-maps columns from validated query results. This is more reliable than guessing `columnMapping`.

When you must pass options:
- **CHART**: only set `globalSeriesType` (e.g. `"line"`, `"column"`, `"pie"`) — do not set `columnMapping` unless column names are confirmed from `run_query`.
- **COUNTER**: omit options; server picks the best numeric column.
- **MAP / CHOROPLETH / FUNNEL / WORD_CLOUD**: set column options only after confirming exact column names from query results.

Fix existing viz:

```text
update_visualization(visualization_id, name?, type?, options?)
```

### 5. Build the dashboard

```text
create_dashboard(name)                                    # starts as draft
add_widget_to_dashboard(dashboard_id, visualization_id)   # auto-places below existing widgets
add_widget_to_dashboard(dashboard_id, text="# Title\n\nIntro markdown")  # text header
get_dashboard(dashboard_id)                               # verify layout + widget ids
update_dashboard(dashboard_id, is_draft=false)              # publish
```

Share the dashboard URL: `/dashboards/{id}-{slug}` (never hash URLs like `/#/dashboards/...`).

## Dashboard grid layout

12-column grid. Positions live in `options.position`:

| Field | Meaning |
|-------|---------|
| `col` | Left column (0–11) |
| `row` | Row index (stacked vertically) |
| `sizeX` | Width in columns (max 12) |
| `sizeY` | Height in row units (~50px each) |

Common layouts (these match the sizes `build_dashboard_from_spec` and auto-placement apply):

- **Full-width chart/table**: `sizeX: 12, sizeY: 8`
- **Two charts side-by-side**: both `sizeX: 6, sizeY: 8`, same `row`, `col: 0` and `col: 6`
- **KPI row**: four `sizeX: 3, sizeY: 8` counters on one row (counters shorter than `sizeY: 8` can render invisibly small)
- **Page title text**: full width `sizeX: 12, sizeY: 3` at `row: 0`; section headers `sizeX: 12, sizeY: 2`

Explicit position example:

```json
{
  "position": {
    "col": 0,
    "row": 3,
    "sizeX": 6,
    "sizeY": 8,
    "minSizeX": 2,
    "maxSizeX": 12,
    "minSizeY": 2,
    "maxSizeY": 1000,
    "autoHeight": false
  }
}
```

Omit `options` on `add_widget_to_dashboard` to auto-place below existing widgets.

Layout edits:

```text
get_dashboard(dashboard_id)           # read layout_summary, widget ids
update_widget(widget_id, text?, options={"position": {...}})
delete_widget(widget_id)
```

## Decision guide: pick the right viz

```
Has date/time column + numeric metric?  → CHART (line or area)
Category labels + numeric values?       → CHART (column/bar) or pie if ≤8 categories
Single aggregate number?                → COUNTER
Separate lat + lon columns?             → MAP
Region codes (US, FR, …) + metric?      → CHOROPLETH
Step names + counts?                    → FUNNEL
Source/target/weight columns?           → SANKEY
Just explore raw data?                  → TABLE (already created)
```

## Pitfalls

- **Wrong column names**: placeholders like `date`, `tvl`, `x_column` fail unless they literally appear in `columns`. Always read `run_query` output first.
- **Empty charts**: query must run successfully and return rows before creating viz. Refresh saved queries if needed.
- **Draft dashboards**: new dashboards are drafts — call `update_dashboard(is_draft=false)` before sharing.
- **GeoJSON geometry**: MAP needs separate lat/lon numeric columns, not raw GeoJSON.
- **Over-specifying options**: prefer server auto-mapping over manual `columnMapping`.

## Checklist

Full dashboard (preferred):

```text
Task Progress:
- [ ] run_query per data source — confirm columns + sample rows
- [ ] build_dashboard_from_spec (queries + derived + widgets)
- [ ] Review warnings in the response; get_dashboard to verify layout
- [ ] Share /dashboards/{id}-{slug} link
```

Incremental (single viz or dashboard edits):

```text
Task Progress:
- [ ] run_query — confirm columns + sample rows
- [ ] create_query (or reuse existing query_id)
- [ ] get_visualization_type if unfamiliar type
- [ ] create_visualization (omit options unless style requested)
- [ ] create_dashboard (if new)
- [ ] add_widget_to_dashboard (viz or text header)
- [ ] get_dashboard — verify layout
- [ ] update_dashboard(is_draft=false) — publish
```

## Additional resources

- Full visualization type catalog and CHART series types: [reference.md](reference.md)
- Demo script with all chart types: `scripts/create_viz_demo_dashboard.py`
