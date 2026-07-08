"""Platform catalog: query runners and visualization types for the assistant."""

from __future__ import annotations

from typing import Any, Optional

try:
    from rewatch.query_runner import query_runners
except ImportError:
    # Flask-free environments (e.g. the standalone MCP server) can still use
    # the static notes/guides below; live runner introspection is skipped.
    query_runners = {}

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
        "generation_rules": [
            "Output valid SQL for the connected database dialect.",
            "Use only table and column names from the provided schema.",
            "Prefer explicit column lists over SELECT * when schema is available.",
        ],
    },
    "yaml": {
        "label": "YAML",
        "summary": "Structured YAML describing API requests or HTTP calls.",
        "tips": [
            "Query text must be valid YAML (not SQL).",
            "Runner-specific keys — call get_query_runner_type; do not assume SQL or generic JSON.",
            "Vendor API runners (CoinGecko, DefiLlama, Dune) use an `endpoint:` key plus path params as top-level keys.",
            "Generic JSON/HTTP runners use `url`, `method`, `path`, `fields`, `params`, `headers`.",
            "Query-string parameters usually go under `params:` unless documented as top-level keys.",
            "Use get_data_source_schema to browse available endpoints; prefer schema templates over inventing URLs.",
            "Always run_query with ad-hoc query_text first to inspect columns before create_query.",
        ],
        "generation_rules": [
            "Output valid YAML only — never SQL, JSON, or markdown fences.",
            "Match the exact key names documented for this data source type (e.g. endpoint, coingeckoID, protocol).",
            "Copy structure from schema templates when an endpoint or coin is listed in the schema.",
            "Path parameters are top-level YAML keys; optional query-string params go under params:.",
            "For CoinGecko, DefiLlama, and Dune: use `endpoint:` syntax — never `url`, `method`, `path`, or `fields` (those belong to the JSON data source type only).",
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
        "generation_rules": [
            "Output valid JSON only — no markdown fences or comments unless the runner allows them.",
            "Follow the runner's documented query object shape exactly.",
        ],
    },
    "graphql": {
        "label": "GraphQL",
        "summary": "GraphQL query string sent to a configured endpoint.",
        "tips": [
            "Write a standard GraphQL query/mutation string.",
            "Variables may be supported depending on the runner — check get_query_runner_type.",
        ],
        "generation_rules": [
            "Output a GraphQL query or mutation string only — not SQL or YAML.",
            "Use field names from get_data_source_schema when available.",
        ],
    },
    "python": {
        "label": "Python",
        "summary": "Python script executed in a sandbox; must produce rows/columns.",
        "tips": [
            "Write Python that returns tabular data compatible with the runner.",
            "Check get_query_runner_type for allowed imports and result format.",
        ],
        "generation_rules": [
            "Output executable Python script text only.",
            "Must return rows/columns in the format expected by the runner.",
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
        "summary": "Query cached results from other saved queries using SQLite SQL.",
        "tips": [
            "Reference other queries as cached_query_<id> tables (uses the stored cached result; fast) "
            "or query_<id> tables (re-executes the child query on every run; slow).",
            "Refresh child queries first so cached results exist — use refresh_queries_and_wait.",
            "SQL dialect is SQLite: no PostgreSQL casts like ::numeric or ::int. "
            "Use ROUND(x, 2), CAST(x AS INTEGER), and standard SELECT/JOIN/WHERE/GROUP BY.",
            "Only queries with cached results appear in schema.",
            "build_dashboard_from_spec handles this automatically via derived queries with "
            "{{cached_query.KEY}} placeholders.",
        ],
        "example_query": "SELECT name, ROUND(tvl / 1e9, 2) AS tvl_b\nFROM cached_query_123\nORDER BY tvl DESC\nLIMIT 25",
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
        "summary": "GraphQL HTTP endpoint (often The Graph protocol subgraphs).",
        "example_query": (
            "{\n"
            "  erc20Transfers(\n"
            "    first: $first\n"
            "    where: { contract: \"0x...\", id_gt: \"$id_gt\" }\n"
            "    orderBy: timestamp\n"
            "    orderDirection: asc\n"
            "  ) {\n"
            "    timestamp\n"
            "    id\n"
            "    value\n"
            "  }\n"
            "}"
        ),
        "tips": [
            "Subgraph entities use cursor pagination: first + id_gt parameters.",
            "Nested objects flatten to dotted columns (e.g. from.id → from_id in results).",
            "Pair with Query Results SQL for daily aggregation and CHART visualizations.",
            "Production pattern: base GraphQL query → derived query_{id} CTE pipeline.",
        ],
    },
    "defillama": {
        "summary": "DefiLlama DeFi analytics REST API (TVL, yields, DEX volumes, stablecoins, etc.).",
        "query_keys": ["endpoint", "params", "protocol", "chain", "coins", "pool", "symbol", "asset", "timestamp"],
        "config_notes": "Free API needs no key (https://api.llama.fi). Pro API key unlocks exclusive endpoints and higher rate limits.",
        "example_query": "endpoint: protocols\n",
        "example_queries": [
            "endpoint: protocols\n",
            "endpoint: protocol\nprotocol: aave\n",
            "endpoint: overview-fees\n",
            "endpoint: prices-current\ncoins: coingecko:ethereum\n",
            "endpoint: historical-chain-tvl-chain\nchain: Ethereum\n",
        ],
        "tips": [
            "Query syntax is YAML with `endpoint:` set to a kebab-case slug (e.g. protocols, overview-fees, prices-current).",
            "Path parameters (protocol, chain, coins, pool, symbol, asset, timestamp) are top-level YAML keys.",
            "Optional query-string parameters go under `params:`.",
            "Schema browser lists endpoints by category (tvl.*, dex.*, coins.*, fees.*, ...); use insert templates from schema.",
            "Do not invent API URLs — pick endpoint slugs from schema or get_query_runner_type endpoint_catalog.",
            "Chain ecosystem dashboard recipe (works well with build_dashboard_from_spec): "
            "`historical-chain-tvl-chain` + chain for TVL history; `overview-dexs-chain` and "
            "`overview-fees-chain` + chain for single-row volume/fee aggregates (total24h, total7d, "
            "change_1d — render as counters); `chains` for cross-chain TVL ranking; `protocols` has "
            "per-chain columns like chainTvls_Ethereum — give it a key and aggregate via derived "
            "queries (top protocols, TVL by category). Combine with a coingecko source for price data.",
        ],
    },
    "coingecko": {
        "summary": "CoinGecko cryptocurrency market data REST API.",
        "query_keys": ["endpoint", "coingeckoID", "coinId", "params"],
        "example_query": "endpoint: simple-price\ncoingeckoID: ethereum\nparams:\n  vs_currencies: usd\n",
        "example_queries": [
            "endpoint: simple-price\ncoingeckoID: ethereum\nparams:\n  vs_currencies: usd\n",
            "endpoint: market-chart\ncoingeckoID: bitcoin\nparams:\n  vs_currency: usd\n  days: 30\n",
            "endpoint: coins-markets\nparams:\n  vs_currency: usd\n  ids: inverse-finance\n",
            "endpoint: coin-detail\ncoingeckoID: inverse-finance\nparams:\n  localization: false\n  tickers: false\n  market_data: true\n",
        ],
        "tips": [
            "Query syntax is YAML with `endpoint:` set to a kebab-case slug (e.g. simple-price, market-chart, coin-detail).",
            "Coin-specific endpoints require `coingeckoID:` (or `coinId:`) with the CoinGecko coin id (e.g. ethereum, inverse-finance).",
            "Optional API params go under `params:` (e.g. vs_currency, days, ids, per_page).",
            "Do NOT use `url`, `method`, `path`, or `fields` — that is JSON data source syntax, not CoinGecko.",
            "For a single coin's market cap, prefer `endpoint: coins-markets` with `params.ids` or `endpoint: coin-detail` with `coingeckoID`.",
            "Schema browser includes endpoint categories (market.*, reference.*, detail.*) and popular coins (coins.*) with insertValue templates.",
            "Use coingeckoID values from schema coins.* entries — do not invent coin ids.",
        ],
    },
    "dune": {
        "summary": "Dune Analytics SQL query execution via API.",
        "query_keys": ["query_id", "query_parameters", "performance"],
        "example_query": "query_id: 1234567\nquery_parameters:\n  chain: ethereum\nperformance: medium\n",
        "tips": [
            "Query syntax is YAML — not raw SQL. You execute a saved Dune query by `query_id`.",
            "Pass Dune query parameters under `query_parameters:`; set `performance` to medium or large.",
        ],
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
        "tips": [
            "Script must define how to fetch/return rows; validate with run_query.",
            "get_query_result(query_id) loads another query's cached {columns, rows}.",
            "Common pattern: pd.DataFrame(get_query_result(N)['rows']) → merge/aggregate → return rows.",
            "Use df_to_result(df) from scripts.tools.common when available.",
            "Production FiRM/Dola dashboards use Python for wide KPI rows + CHART outputs.",
            "Call list_instance_examples(category='python') for chaining examples.",
        ],
        "example_query": (
            "import pandas as pd\n"
            "\n"
            "raw = get_query_result(123)\n"
            "df = pd.DataFrame(raw['rows'])\n"
            "summary = df.groupby('day').agg(total=('value', 'sum')).reset_index()\n"
            "return summary.to_dict('records')"
        ),
    },
    "evmlogs": {
        "summary": "Scan EVM event logs across configured chains.",
        "query_keys": ["contract_address", "event_name", "start_block", "end_block"],
        "example_query": (
            'contract_address: "0x865377367054516e17014ccded1e7d814edc9ce4"\n'
            "event_name: Transfer\n"
            "start_block: -1000\n"
            "end_block: 'latest'"
        ),
        "tips": [
            "YAML-style keys — not SQL. contract_address accepts one address or a list.",
            "start_block: -N scans the last N blocks; end_block: 'latest' is common.",
            "Use {{parameter}} placeholders for reusable event-scan templates.",
            "Aggregate in Query Results SQL (query_{id}) for time-series charts.",
            "Production: Transfer, PoolBalanceChanged, TokenBridge events → derived burns/volume.",
        ],
    },
    "evmstate": {
        "summary": "Read EVM contract state (balances, view functions) across blocks.",
        "query_keys": [
            "contract_address",
            "implementation_address",
            "function_name",
            "args",
            "start_block",
            "end_block",
        ],
        "example_query": (
            "contract_address: {{contract_address}}\n"
            "implementation_address: {{implementation_address}}\n"
            "function_name: balanceOf\n"
            'args: "0x..."\n'
            "start_block: -500\n"
            "end_block: 'latest'"
        ),
        "tips": [
            "Returns block_time + value columns — chart with contract_address as series.",
            "param_query_* templates parameterize contract_address and function_name.",
            "Treasury monitoring: multiple addresses in one query, USD conversion in derived SQL.",
            "columnMapping for multi-contract lines: block_time→x, value→y, contract_address→series.",
        ],
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
        "summary": "ECharts-based charts (column, line, bar, area, pie, scatter).",
        "required_options": ["columnMapping"],
        "common_options": {
            "globalSeriesType": "line | column | bar | area | pie | scatter",
            "columnMapping": {"<x_column>": "x", "<y_column>": "y"},
            "legend": {"enabled": True},
            "sortX": True,
        },
        "example_options": {
            "globalSeriesType": "line",
            "columnMapping": {"date": "x", "tvl": "y"},
            "legend": {"enabled": True},
            "sortX": True,
        },
        "example_counter_options": {
            "counterColName": "market_cap.usd",
            "counterLabel": "Market cap",
            "rowNumber": 1,
            "targetRowNumber": 1,
        },
        "tips": [
            "columnMapping keys are exact result column names from validation.columns (case-sensitive, dots allowed).",
            "Values are roles: x, y, series — not column names.",
            "Prefer omitting options in create_visualization; the server auto-maps columns from query results.",
            "Read visualization_hints.recommended.CHART from run_query before creating charts.",
            "Prefer line charts for time series (date + numeric); column/bar for categories.",
        ],
    },
    "COUNTER": {
        "name": "Counter",
        "summary": "Single KPI number from one row/column.",
        "required_options": [],
        "common_options": {
            "counterLabel": "",
            "counterColName": "exact_numeric_column_from_validation.columns",
            "rowNumber": 1,
            "targetRowNumber": 1,
        },
        "tips": [
            "counterColName must be an exact column name from validation.columns (e.g. market_cap.usd).",
            "Omit options in create_visualization — the server picks the best numeric column.",
        ],
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


def _endpoint_catalog_for_runner(runner_type: str) -> list[dict[str, Any]]:
    """Compact endpoint list for API-style YAML runners."""
    runner_type = (runner_type or "").lower()
    try:
        return _endpoint_catalog_for_runner_impl(runner_type)
    except ImportError:
        return []


def _endpoint_catalog_for_runner_impl(runner_type: str) -> list[dict[str, Any]]:
    if runner_type == "defillama":
        from rewatch.query_runner.defillama import DEFILLAMA_ENDPOINTS, _schema_for_endpoint

        return [
            {
                "category": entry["category"],
                "endpoint": entry["slug"],
                "description": entry.get("description"),
                "path_params": [p["name"] for p in entry.get("path_params", [])],
                "pro_only": bool(entry.get("pro_only")),
                "example_query": _schema_for_endpoint(entry)["insertValue"].strip(),
            }
            for entry in DEFILLAMA_ENDPOINTS
        ]
    if runner_type == "coingecko":
        from rewatch.query_runner.coingecko import COINGECKO_ENDPOINT_CATALOG, _coingecko_schema_for_endpoint

        return [
            {
                "category": entry["category"],
                "endpoint": entry["slug"],
                "description": entry.get("description"),
                "path_params": [p["name"] for p in entry.get("params", [])],
                "example_query": _coingecko_schema_for_endpoint(entry)["insertValue"].strip(),
            }
            for entry in COINGECKO_ENDPOINT_CATALOG
        ]
    return []


def build_query_generation_context(runner_type: str, syntax: Optional[str] = None) -> dict[str, Any]:
    """Rich, syntax-aware context for LLM query generation."""
    runner_type = (runner_type or "").strip().lower()
    runner_cls = _runner_class(runner_type)
    if runner_cls is None:
        syntax = syntax or "sql"
        syntax_guide = QUERY_SYNTAX_GUIDES.get(syntax, QUERY_SYNTAX_GUIDES["custom"])
        return {
            "syntax": syntax,
            "syntax_label": syntax_guide.get("label", syntax),
            "generation_rules": syntax_guide.get("generation_rules", []),
        }

    resolved_syntax = syntax or _runner_syntax(runner_cls)
    syntax_guide = QUERY_SYNTAX_GUIDES.get(resolved_syntax, QUERY_SYNTAX_GUIDES["custom"])
    notes = dict(QUERY_RUNNER_NOTES.get(runner_type, {}))

    examples: list[str] = []
    if notes.get("example_query"):
        examples.append(str(notes["example_query"]))
    examples.extend(notes.get("example_queries") or [])

    endpoint_catalog = _endpoint_catalog_for_runner(runner_type)

    return {
        "type": runner_cls.type(),
        "name": runner_cls.name(),
        "syntax": resolved_syntax,
        "syntax_label": syntax_guide.get("label", resolved_syntax),
        "summary": notes.get("summary") or syntax_guide.get("summary"),
        "query_keys": notes.get("query_keys") or [],
        "config_notes": notes.get("config_notes"),
        "tips": (notes.get("tips") or []) + (syntax_guide.get("tips") or [])[:4],
        "generation_rules": syntax_guide.get("generation_rules") or [],
        "example_queries": examples[:6],
        "endpoint_catalog": endpoint_catalog[:40],
        "schema_hint": (
            "Schema entries may include YAML templates under insertValue — prefer those over inventing queries."
            if resolved_syntax == "yaml"
            else "Use table and column names from schema exactly."
        ),
    }


def _notes_only_summary(runner_type: str) -> Optional[dict[str, Any]]:
    """Fallback catalog entry from static notes when live runners are unavailable."""
    notes = QUERY_RUNNER_NOTES.get(runner_type)
    if not notes:
        return None
    result: dict[str, Any] = {
        "type": runner_type,
        "name": runner_type,
        "summary": notes.get("summary"),
        "tips": list(notes.get("tips") or [])[:8],
    }
    if notes.get("example_query"):
        result["example_query"] = notes["example_query"]
    if notes.get("query_keys"):
        result["query_keys"] = notes["query_keys"]
    return result


def summarize_runner_for_type(runner_type: str) -> Optional[dict[str, Any]]:
    """Compact catalog entry for embedding in data source payloads."""
    runner_cls = _runner_class(runner_type)
    if runner_cls is None:
        if not query_runners:
            return _notes_only_summary((runner_type or "").lower())
        return None

    syntax = _runner_syntax(runner_cls)
    syntax_guide = QUERY_SYNTAX_GUIDES.get(syntax, QUERY_SYNTAX_GUIDES["custom"])
    notes = QUERY_RUNNER_NOTES.get(runner_type.lower(), {})

    summary = notes.get("summary") or syntax_guide.get("summary")
    tips = list(notes.get("tips") or []) + list(syntax_guide.get("tips") or [])

    result: dict[str, Any] = {
        "type": runner_cls.type(),
        "name": runner_cls.name(),
        "syntax": syntax,
        "syntax_label": syntax_guide.get("label", syntax),
        "summary": summary,
        "tips": tips[:8],
        "schema_fields": _summarize_config_schema(runner_cls.configuration_schema()),
        "deprecated": bool(getattr(runner_cls, "deprecated", False)),
    }
    if notes.get("example_query"):
        result["example_query"] = notes["example_query"]
    if notes.get("query_keys"):
        result["query_keys"] = notes["query_keys"]
    return result


def list_query_runner_types(query: Optional[str] = None) -> dict[str, Any]:
    """All registered query runner types (optionally filtered)."""
    items: list[dict[str, Any]] = []
    for runner_type in sorted(query_runners.keys() or QUERY_RUNNER_NOTES.keys()):
        runner_cls = query_runners.get(runner_type)
        syntax = _runner_syntax(runner_cls)
        name = runner_cls.name() if runner_cls is not None else runner_type
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
        if not query_runners and runner_type in QUERY_RUNNER_NOTES:
            notes = dict(QUERY_RUNNER_NOTES[runner_type])
            base = _notes_only_summary(runner_type) or {"type": runner_type}
            base["type_notes"] = notes
            endpoint_catalog = _endpoint_catalog_for_runner(runner_type)
            if endpoint_catalog:
                base["endpoint_catalog"] = endpoint_catalog
            return base
        known = sorted(query_runners.keys()) or sorted(QUERY_RUNNER_NOTES.keys())
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
        else "Use get_data_source_schema to browse endpoints/templates, then run_query to discover result columns."
    )
    endpoint_catalog = _endpoint_catalog_for_runner(runner_type)
    if endpoint_catalog:
        base["endpoint_catalog"] = endpoint_catalog
    if runner_type == "coingecko":
        base["query_syntax"] = (
            "YAML with `endpoint:` (kebab-case slug) and, for coin-specific calls, `coingeckoID:`. "
            "Do not use `url`, `method`, `path`, or `fields` — those keys are for the JSON data source type only."
        )
    elif runner_type == "defillama":
        base["query_syntax"] = (
            "YAML with `endpoint:` (kebab-case slug) and path params as top-level keys "
            "(e.g. protocol, chain, coins). Optional query-string params go under `params:`."
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
    result = {"type": viz_type, **meta}
    result["dashboard_workflow"] = (
        "Full dashboards (3+ widgets): prefer build_dashboard_from_spec — one call validates queries, "
        "creates visualizations and widgets with a curated grid layout, and publishes. "
        "Incremental flow: run_query or create_query (read validation columns) → create_visualization "
        "→ add_widget_to_dashboard → get_dashboard to verify layout → update_dashboard(is_draft=false) to publish."
    )
    return result
