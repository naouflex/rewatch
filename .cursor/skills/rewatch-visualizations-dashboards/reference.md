# Rewatch Visualization Reference

## MCP tools (user-rewatch)

| Tool | Purpose |
|------|---------|
| `run_query` | Execute ad-hoc or saved query; inspect columns/rows |
| `list_data_sources` | Find data source id + type |
| `get_data_source_schema` | Discover tables/columns (SQL sources) |
| `create_query` / `update_query` | Save query text |
| `list_visualization_types` | Browse all viz types |
| `get_visualization_type` | Options schema for one type |
| `create_visualization` | Attach viz to a query |
| `update_visualization` | Change name/type/options |
| `create_dashboard` | New dashboard (draft) |
| `get_dashboard` | Widgets, layout, viz references |
| `add_widget_to_dashboard` | Add chart/table or text widget |
| `update_widget` | Move/resize text widgets |
| `delete_widget` | Remove widget |
| `update_dashboard` | Publish (`is_draft=false`), rename, tags |

## Visualization types

### TABLE

Default for new queries. No options required.

### CHART (ECharts)

**Required**: `columnMapping` (auto-generated if omitted).

**Common options**:

```json
{
  "globalSeriesType": "line",
  "columnMapping": {"date": "x", "tvl": "y", "protocol": "series"},
  "legend": {"enabled": true},
  "sortX": true,
  "xAxis": {"type": "datetime", "labels": {"enabled": true}}
}
```

`columnMapping` keys = **exact result column names**. Values = roles: `x`, `y`, `series` (not column names).

**globalSeriesType values** (common):

| Type | Use case |
|------|----------|
| `line` | Time series |
| `area` | Stacked time series |
| `column` / `bar` | Categories |
| `pie` | Part-of-whole (few categories) |
| `scatter` / `effectScatter` | XY correlation |
| `bubble` | XY + size column (role `size`) |
| `heatmap` | Grid x × y × intensity (role `zVal`) |
| `candlestick` | OHLC: roles `open`, `high`, `low`, `close` |
| `radar` | Multi-axis comparison |
| `gauge` | Single KPI dial |
| `treemap` | Hierarchical categories |
| `themeRiver` | Stacked streams over time |
| `parallel` | Multi-dimensional rows |
| `box` | Distribution per category |
| `pictorialBar` | Decorative bar chart |

**xAxis.type**: `"datetime"` for dates, `"category"` for labels.

### COUNTER

Single KPI from one row/column.

```json
{
  "counterColName": "market_cap.usd",
  "counterLabel": "Market cap",
  "rowNumber": 1,
  "targetRowNumber": 1
}
```

Omit options — server picks the best numeric column.

### MAP

Point markers on Leaflet map.

```json
{
  "latColName": "geo.lat",
  "lonColName": "geo.lng",
  "clusterMarkers": true
}
```

Requires separate numeric lat/lon columns. Raw GeoJSON geometry does not work.

### CHOROPLETH

Region map colored by value.

```json
{
  "mapType": "countries",
  "keyColumn": "country_code",
  "targetField": "iso_a2",
  "valueColumn": "gdp"
}
```

`keyColumn` values must match map region identifiers (ISO codes for countries).

### FUNNEL

```json
{
  "stepCol": {"colName": "step", "displayAs": "Step"},
  "valueCol": {"colName": "value", "displayAs": "Users"}
}
```

### SANKEY / SUNBURST_SEQUENCE

Flow and hierarchy viz. Often work with empty options when query shape matches (multi-stage columns + value). See `scripts/create_viz_demo_dashboard.py` for query shapes.

### WORD_CLOUD

```json
{
  "column": "word",
  "frequenciesColumn": "count"
}
```

### BOXPLOT

Dedicated type (not CHART box series). Query: group column + measurement column.

### PIVOT / COHORT / DETAILS / GRAPH

Specialized types — call `get_visualization_type` before use. COHORT needs specific time/cohort column shape.

## Example queries by viz type

### Time series (multi-series line)

```sql
SELECT d::date AS date, s AS series, v AS value
FROM (VALUES
  ('2024-01-01','Alpha',10),('2024-02-01','Alpha',14),
  ('2024-01-01','Beta',8),('2024-02-01','Beta',11)
) AS t(d, s, v)
ORDER BY 1, 2
```

→ `CHART` with `globalSeriesType: "line"` (omit columnMapping).

### Categories (pie/column)

```sql
SELECT category, value FROM (VALUES
  ('Apple',45),('Banana',32),('Cherry',28)
) AS t(category, value)
ORDER BY value DESC
```

### KPI counter

```sql
SELECT 73 AS completion_pct
```

→ `COUNTER` (omit options).

### Choropleth

```sql
SELECT country_code, gdp FROM (VALUES
  ('US',21000),('FR',2700),('DE',3800)
) AS t(country_code, gdp)
```

→ `CHOROPLETH` with `keyColumn: "country_code"`, `valueColumn: "gdp"`.

## Dashboard widget API shape

Visualization widget:

```json
{
  "dashboard_id": 1,
  "visualization_id": 42,
  "options": {
    "position": {"col": 0, "row": 0, "sizeX": 6, "sizeY": 8}
  },
  "width": 1
}
```

Text widget:

```json
{
  "dashboard_id": 1,
  "visualization_id": null,
  "text": "# Dashboard Title\n\nDescription markdown.",
  "options": {"position": {"col": 0, "row": 0, "sizeX": 12, "sizeY": 3}},
  "width": 1
}
```

## Grid constants

- Columns: **12**
- Row height: **~50px**
- Default widget: **6 × 3** (half width, 3 row units)
- Min size: **2 × 2**
- Max width: **12**

## Server auto-mapping behavior

When `create_visualization` is called without options (or with partial options):

1. Query is executed to get `columns` + sample `rows`
2. Server infers best x/y/series columns by name heuristics (date hints, numeric hints, lat/lon hints)
3. Wrong or placeholder column names are corrected or dropped
4. Response may include `auto_suggested_options` and `column_corrections`

Prefer omitting options over manual mapping — the server knows exact column names from validation.
