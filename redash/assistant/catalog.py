"""Platform catalog: query runners and visualization types for the assistant."""

from __future__ import annotations

from typing import Any, Optional

from rewatch.query_runner import query_runners

# --- Query syntax (shared across many data source types) ---

QUERY_SYNTAX_GUIDES: dict[str, dict[str, Any]] = {
    "sql": {
        "label": "SQL",
        "summary": "Standard SQL against relational/analytical databases.",
        "tips": [
            "Use get_data_source_schema to discover tables and columns before writing queries.",
            "Test with run_query (query_text + data_source_id) before create_query.",
            "Multiple statements are supported; only the last SELECT result is shown.",
            "Auto LIMIT may be applied on SELECT queries without LIMIT.",
        ],
    },
    "yaml": {
        "label": "YAML",
        "summary": "Structured YAML describing HTTP requests, paths, and field selection.",
        "tips": [
            "Query text must be valid YAML (not SQL).",
            "Most YAML runners require a `url` key; it can be absolute or relative to the data source base URL.",
            "Common keys: url, method (get/post), path (dot path to rows array), fields (column whitelist), params, headers.",
            "Nested JSON objects become dotted column names (e.g. geo.lat, address.city).",
            "Always run_query with ad-hoc query_text first to inspect columns before create_query.",
        ],
    },
    "json": {
        "label": "JSON",
        "summary": "JSON document describing the query (MongoDB, Elasticsearch, JQL, etc.).",
        "tips": [
            "Query text must be valid JSON (not SQL).",
            "Structure is runner-specific — call get_query_runner_type for the exact data source type.",
            "Validate with run_query before create_query.",
        ],
    },
    "graphql": {
        "label": "GraphQL",
        "summary": "GraphQL query string sent to a configured endpoint.",
        "tips": [
            "Write a standard GraphQL query/mutation string.",
            "Variables may be supported depending on the runner — check get_query_runner_type.",
        ],
    },
    "python": {
        "label": "Python",
        "summary": "Python script executed in a sandbox; must produce rows/columns.",
        "tips": [
            "Write Python that returns tabular data compatible with the runner.",
            "Check get_query_runner_type for allowed imports and result format.",
        ],
    },
    "custom": {
        "label": "Custom",
        "summary": "Proprietary query language for this integration.",
        "tips": [
            "Always call get_query_runner_type for the exact type before writing query text.",
            "Use run_query to validate before create_query.",
        ],
    },
}

# Per-type notes beyond syntax (keyed by query runner `type` string).
QUERY_RUNNER_NOTES: dict[str, dict[str, Any]] = {
    "json": {
        "summary": "Fetch and parse JSON from HTTP URLs.",
        "query_keys": ["url", "method", "path", "fields", "params", "headers", "pagination"],
        "config_notes": "Optional base_url in data source options; relative urls are joined to it.",
        "example_query": (
            "url: https://jsonplaceholder.typicode.com/users\n"
            "fields:\n"
            "  - name\n"
            "  - geo.lat\n"
            "  - geo.lng\n"
            "  - address.city"
        ),
        "visualization_hints": {
            "MAP": "Use numeric lat/lon columns (e.g. geo.lat, geo.lng). Raw GeoJSON geometry is not directly usable.",
            "CHART": "Map date/metric columns via options.columnMapping after validation.",
        },
        "workflow": [
            "list_data_sources → pick type `json`",
            "web_search + fetch_url to find public JSON endpoints",
            "run_query with YAML query_text to inspect columns",
            "create_query → create_visualization",
        ],
    },
    "results": {
        "summary": "Query cached results from other saved queries using SQL-like syntax.",
        "tips": [
            "Reference other queries as tables named query_<id> (see get_data_source_schema).",
            "Standard SQL SELECT/JOIN/WHERE against those virtual tables.",
            "Only queries with cached results appear in schema.",
        ],
        "example_query": "SELECT * FROM query_123 LIMIT 100",
    },
    "mongodb": {
        "summary": "MongoDB aggregation/find queries as JSON.",
        "tips": [
            "Query is a JSON object with collection, query, fields, sort, limit, aggregate, etc.",
            "Use ISODate(\"...\") for date literals in JSON.",
        ],
    },
    "google_spreadsheets": {
        "summary": "Google Sheets via spreadsheet key and worksheet reference.",
        "tips": [
            "Custom syntax: spreadsheet URL/key plus worksheet name or index.",
            "Call get_query_runner_type and inspect schema after connecting.",
        ],
    },
    "graphql": {
        "summary": "GraphQL HTTP endpoint.",
        "example_query": "query {\n  users {\n    id\n    name\n  }\n}",
    },
    "elasticsearch": {
        "summary": "Elasticsearch query DSL as JSON.",
        "tips": ["Use JSON query DSL; index name typically configured on the data source."],
    },
    "elasticsearch2": {
        "summary": "Elasticsearch via HTTP (JSON query DSL or SQL depending on variant).",
        "tips": ["Check data source name/type variant — some support SQL (OpenDistro/X-Pack)."],
    },
    "python": {
        "summary": "Python script data source.",
        "tips": ["Script must define how to fetch/return rows; validate with run_query."],
    },
    "script": {
        "summary": "Shell/script runner.",
        "tips": ["Runner-specific; validate output columns with run_query."],
    },
}

VISUALIZATION_TYPES: dict[str, dict[str, Any]] = {
    "TABLE": {
        "name": "Table",
        "summary": "Default for new queries. Shows all result columns as rows.",
        "required_options": [],
        "common_options": {},
    },
    "CHART": {
        "name": "Chart",
        "summary": "Plotly-based charts (column, line, bar, area, pie, scatter).",
        "required_options": ["columnMapping"],
        "common_options": {
            "columnMapping": {"date_col": "x", "metric_col": "y"},
            "globalSeriesType": "column | line | bar | area | pie | scatter",
            "legend": {"enabled": True},
        },
        "tips": [
            "Query must validate first; use validation columns for columnMapping keys.",
            "globalSeriesType controls chart style.",
        ],
    },
    "COUNTER": {
        "name": "Counter",
        "summary": "Single KPI number from one row/column.",
        "required_options": [],
        "common_options": {
            "counterLabel": "",
            "counterColName": "column_with_value",
            "rowNumber": 1,
            "targetRowNumber": 1,
        },
    },
    "MAP": {
        "name": "Map (markers)",
        "summary": "Leaflet map with lat/lon markers from query rows.",
        "required_options": ["latColName", "lonColName"],
        "common_options": {
            "latColName": "lat",
            "lonColName": "lon",
            "classify": "optional column for color grouping",
            "clusterMarkers": True,
        },
        "tips": [
            "latColName and lonColName must match numeric columns from validated query results.",
            "Prefer datasets with separate lat/lon fields (geo.lat, geo.lng), not raw GeoJSON geometry.",
        ],
    },
    "CHOROPLETH": {
        "name": "Choropleth map",
        "summary": "Region/shape map colored by a value column (countries, states, etc.).",
        "required_options": ["keyColumn", "valueColumn"],
        "common_options": {
            "mapType": "countries",
            "keyColumn": "region_code_column",
            "targetField": "iso field on map shapes",
            "valueColumn": "metric_column",
        },
        "tips": [
            "Use for aggregated data by region code, not point lat/lon.",
            "keyColumn values must match the map's region identifiers.",
        ],
    },
    "PIVOT": {
        "name": "Pivot table",
        "summary": "Cross-tabulation of rows/columns/values.",
        "common_options": {"rows": [], "columns": [], "values": []},
    },
    "FUNNEL": {
        "name": "Funnel",
        "summary": "Step funnel chart.",
        "common_options": {"stepCol": "", "valueCol": ""},
    },
    "COHORT": {
        "name": "Cohort",
        "summary": "Cohort retention matrix.",
        "tips": ["Requires time and cohort columns in a specific shape — validate query first."],
    },
    "DETAILS": {
        "name": "Details",
        "summary": "Master/detail view linked to another visualization.",
    },
    "SANKEY": {
        "name": "Sankey",
        "summary": "Flow diagram (source → target → value).",
        "common_options": {"sourceCol": "", "targetCol": "", "weightCol": ""},
    },
    "BOXPLOT": {
        "name": "Box plot",
        "summary": "Distribution box plots per category.",
    },
    "GRAPH": {
        "name": "Graph",
        "summary": "Node/link network graph.",
    },
    "WORD_CLOUD": {
        "name": "Word cloud",
        "summary": "Text frequency visualization.",
        "common_options": {"column": "text_column"},
    },
    "SUNBURST_SEQUENCE": {
        "name": "Sunburst",
        "summary": "Hierarchical sunburst chart.",
    },
}


def _runner_class(runner_type: str):
    return query_runners.get((runner_type or "").lower())


def _runner_syntax(runner_cls) -> str:
    if runner_cls is None:
        return "sql"
    try:
        instance = runner_cls({})
        return getattr(instance, "syntax", "sql") or "sql"
    except Exception:
        return "sql"


def _summarize_config_schema(schema: Any) -> dict[str, str]:
    if not isinstance(schema, dict):
        return {}
    props = schema.get("properties") or {}
    result: dict[str, str] = {}
    for key, meta in props.items():
        if isinstance(meta, dict):
            result[key] = str(meta.get("title") or key)
    return result


def _match_filter(text: str, query: str) -> bool:
    q = (query or "").strip().lower()
    if not q:
        return True
    return q in text.lower()


def summarize_runner_for_type(runner_type: str) -> Optional[dict[str, Any]]:
    """Compact catalog entry for embedding in data source payloads."""
    runner_cls = _runner_class(runner_type)
    if runner_cls is None:
        return None

    syntax = _runner_syntax(runner_cls)
    syntax_guide = QUERY_SYNTAX_GUIDES.get(syntax, QUERY_SYNTAX_GUIDES["custom"])
    notes = QUERY_RUNNER_NOTES.get(runner_type.lower(), {})

    summary = notes.get("summary") or syntax_guide.get("summary")
    tips = list(notes.get("tips") or []) + list(syntax_guide.get("tips") or [])

    return {
        "type": runner_cls.type(),
        "name": runner_cls.name(),
        "syntax": syntax,
        "syntax_label": syntax_guide.get("label", syntax),
        "summary": summary,
        "tips": tips[:8],
        "schema_fields": _summarize_config_schema(runner_cls.configuration_schema()),
        "deprecated": bool(getattr(runner_cls, "deprecated", False)),
    }


def list_query_runner_types(query: Optional[str] = None) -> dict[str, Any]:
    """All registered query runner types (optionally filtered)."""
    items: list[dict[str, Any]] = []
    for runner_type in sorted(query_runners.keys()):
        runner_cls = query_runners[runner_type]
        syntax = _runner_syntax(runner_cls)
        name = runner_cls.name()
        haystack = f"{runner_type} {name} {syntax}"
        if not _match_filter(haystack, query or ""):
            continue
        notes = QUERY_RUNNER_NOTES.get(runner_type, {})
        items.append(
            {
                "type": runner_type,
                "name": name,
                "syntax": syntax,
                "summary": notes.get("summary") or QUERY_SYNTAX_GUIDES.get(syntax, {}).get("summary"),
                "deprecated": bool(getattr(runner_cls, "deprecated", False)),
            }
        )
    return {
        "query_runner_types": items,
        "count": len(items),
        "assistant_note": (
            "Call get_query_runner_type(type) before writing query text for an unfamiliar data source. "
            "Match `type` to the `type` field on list_data_sources entries."
        ),
    }


def get_query_runner_type(runner_type: str) -> dict[str, Any]:
    """Full catalog entry for one query runner type."""
    runner_type = (runner_type or "").strip().lower()
    runner_cls = _runner_class(runner_type)
    if runner_cls is None:
        known = sorted(query_runners.keys())
        return {
            "error": f"Unknown query runner type {runner_type!r}.",
            "known_types": known[:40],
            "hint": "Call list_query_runner_types to browse available types.",
        }

    syntax = _runner_syntax(runner_cls)
    syntax_guide = dict(QUERY_SYNTAX_GUIDES.get(syntax, QUERY_SYNTAX_GUIDES["custom"]))
    notes = dict(QUERY_RUNNER_NOTES.get(runner_type, {}))
    base = runner_cls.to_dict()
    base["syntax"] = syntax
    base["syntax_guide"] = syntax_guide
    base["type_notes"] = notes
    base["config_field_labels"] = _summarize_config_schema(base.get("configuration_schema"))
    base["schema_tool"] = (
        "Use get_data_source_schema with a connected data source of this type to list tables/columns."
        if syntax == "sql"
        else "Use run_query with ad-hoc query_text to discover result columns."
    )
    return base


def list_visualization_types(query: Optional[str] = None) -> dict[str, Any]:
    items: list[dict[str, Any]] = []
    for viz_type, meta in VISUALIZATION_TYPES.items():
        haystack = f"{viz_type} {meta.get('name', '')} {meta.get('summary', '')}"
        if not _match_filter(haystack, query or ""):
            continue
        items.append({"type": viz_type, **{k: v for k, v in meta.items() if k != "tips"}})
    return {
        "visualization_types": items,
        "count": len(items),
        "assistant_note": "Call get_visualization_type(type) before create_visualization for unfamiliar types.",
    }


def get_visualization_type(viz_type: str) -> dict[str, Any]:
    viz_type = (viz_type or "").strip().upper()
    meta = VISUALIZATION_TYPES.get(viz_type)
    if meta is None:
        return {
            "error": f"Unknown visualization type {viz_type!r}.",
            "known_types": sorted(VISUALIZATION_TYPES.keys()),
            "hint": "Call list_visualization_types to browse available types.",
        }
    return {"type": viz_type, **meta}
