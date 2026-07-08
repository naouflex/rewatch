"""Curated query and visualization patterns from a production Rewatch instance.

Sourced read-only from a live deployment (Inverse Watch / analytics org) to teach
the assistant how real queries, derived SQL, charts, counters, and dashboard
layouts are built. IDs and snippets are illustrative — always resolve current
data_source_id values with list_data_sources in the target workspace.
"""

from __future__ import annotations

from typing import Any, Optional

INSTANCE_EXAMPLES: list[dict[str, Any]] = [
    {
        "id": "results_derived_cte",
        "category": "query_results",
        "name": "Derived SQL on cached query tables (CTE pipeline)",
        "summary": (
            "Most common analytics pattern: base GraphQL/Python queries cached, "
            "then Query Results SQL aggregates with query_{id} or cached_query_{id}."
        ),
        "data_source_types": ["results", "graphql", "python"],
        "frequency": "252 active queries on Query Results source",
        "patterns": [
            "Base query ingests raw events (GraphQL subgraph or EVM logs)",
            "Derived query uses WITH ... AS (SELECT ... FROM query_{child_id})",
            "Use SUM/COUNT OVER for cumulative metrics; DATE() for daily rollups",
            "SQLite dialect — ROUND(x, 2), no ::numeric casts",
            "refresh_queries_and_wait on child IDs before derived query validates",
        ],
        "query_example": (
            "WITH RECURSIVE\n"
            "data AS (\n"
            "    SELECT\n"
            "        \"erc20Transfers_timestamp\" AS block_time,\n"
            "        SUM(\"erc20Transfers_value\") AS amount_burned\n"
            "    FROM query_1130\n"
            "    GROUP BY 1\n"
            "),\n"
            "cumulative_data AS (\n"
            "    SELECT\n"
            "        *,\n"
            "        SUM(amount_burned) OVER (ORDER BY block_time) AS cumulated_amount_burned\n"
            "    FROM data\n"
            ")\n"
            "SELECT DATE(block_time) AS day, MAX(cumulated_amount_burned) AS cumulated_burn\n"
            "FROM cumulative_data\n"
            "GROUP BY 1\n"
            "ORDER BY 1"
        ),
        "visualization_example": {
            "type": "CHART",
            "name": "Cumulative Burns",
            "chart_type": "area",
            "column_mapping": {"day": "x", "cumulated_burn": "y"},
        },
        "production_refs": ["dbr_daily_burns", "TWG Revenue calculation", "sdola_daily_cost"],
    },
    {
        "id": "python_get_query_result",
        "category": "python",
        "name": "Python query chaining with get_query_result",
        "summary": (
            "Python queries combine multiple cached query results in pandas, "
            "then return a new table for charts/counters."
        ),
        "data_source_types": ["python", "results"],
        "frequency": "42 active Python queries",
        "patterns": [
            "get_query_result(query_id) returns {columns, rows} dict",
            "pd.DataFrame(result['rows']) — join/filter/aggregate in Python",
            "Use df_to_result(df) helper when available in scripts.tools.common",
            "Often paired with COUNTER + CHART visualizations on the Python output",
            "Downstream Query Results SQL can further aggregate Python output",
        ],
        "query_example": (
            "import pandas as pd\n"
            "\n"
            "dbr_transaction = get_query_result(347)\n"
            "borrow_transaction = get_query_result(135)\n"
            "\n"
            "dbr_df = pd.DataFrame(dbr_transaction['rows'])\n"
            "borrow_df = pd.DataFrame(borrow_transaction['rows'])\n"
            "\n"
            "# merge, filter, compute metrics...\n"
            "result = merged.groupby('day').agg(claimed=('amount', 'sum')).reset_index()\n"
            "return result.to_dict('records')"
        ),
        "visualization_example": {
            "type": "CHART",
            "name": "Claimed DBR",
            "chart_type": "area",
            "column_mapping": {"day": "x", "claimed": "y"},
        },
        "production_refs": ["dbr_claims", "FiRM Positions", "cvx_bad_debt_evolution"],
    },
    {
        "id": "evm_logs_events",
        "category": "evmlogs",
        "name": "EVM log event scans with block ranges",
        "summary": "YAML-style queries on evmlogs sources for Transfer and custom events.",
        "data_source_types": ["evmlogs"],
        "frequency": "52 active evmlogs queries across Ethereum, Base, Arbitrum, etc.",
        "patterns": [
            "contract_address: single address, list, or {{parameter}}",
            "event_name: Solidity event name (e.g. Transfer, PoolBalanceChanged)",
            "start_block: -N (relative) or explicit number; end_block: 'latest'",
            "Parameterized templates: param_query_event_all with {{contract_address}}",
            "Feed into Query Results for daily/hourly aggregation",
        ],
        "query_example": (
            'contract_address: "0x865377367054516e17014ccded1e7d814edc9ce4"\n'
            "event_name: Transfer\n"
            "start_block: -1000\n"
            "end_block: 'latest'"
        ),
        "visualization_example": {
            "type": "TABLE",
            "name": "Recent Transfers",
        },
        "production_refs": ["transfers_30_blocks", "poolbalancechanged", "multisigs_inverse"],
    },
    {
        "id": "evm_state_balances",
        "category": "evmstate",
        "name": "EVM state balance / function calls over time",
        "summary": "Track token balances and contract state across blocks for treasury monitoring.",
        "data_source_types": ["evmstate", "results"],
        "frequency": "38 active evmstate queries",
        "patterns": [
            "contract_address + implementation_address + function_name + args",
            "Produces block_time, value columns — chart with series by contract_address",
            "columnMapping: block_time→x, value→y, contract_address→series",
            "Often aggregated to USD in a derived Query Results query",
        ],
        "query_example": (
            "contract_address: {{contract_address}}\n"
            "implementation_address: {{implementation_address}}\n"
            "function_name: balanceOf\n"
            'args: "0xa36b60a14a1a5247912584768c6e5..."'
        ),
        "visualization_example": {
            "type": "CHART",
            "name": "Treasury Balances",
            "chart_type": "line",
            "column_mapping": {
                "block_time": "x",
                "value": "y",
                "contract_address": "series",
            },
        },
        "production_refs": ["treasury_balances", "token_decimals"],
    },
    {
        "id": "graphql_subgraph_pagination",
        "category": "graphql",
        "name": "GraphQL subgraph with cursor pagination",
        "summary": "Inverse Governance / protocol subgraphs with first/id_gt parameters.",
        "data_source_types": ["graphql"],
        "frequency": "32 active GraphQL queries",
        "patterns": [
            "Use first: $first and id_gt: \"$id_gt\" for incremental sync",
            "where: { contract: \"0x...\" } filters on-chain entities",
            "Nested fields flattened to dotted columns (e.g. erc20Transfers_timestamp)",
            "Pair with Query Results SQL for time-series charts",
        ],
        "query_example": (
            "{\n"
            "  erc20Transfers(\n"
            "    first: $first\n"
            "    where: {\n"
            '      contract: "0x865377367054516e17014ccded1e7d814edc9ce4"\n'
            '      id_gt: "$id_gt"\n'
            "    }\n"
            "    orderBy: timestamp\n"
            "    orderDirection: asc\n"
            "  ) {\n"
            "    timestamp\n"
            "    id\n"
            "    value\n"
            "    from { id }\n"
            "    to { id }\n"
            "  }\n"
            "}"
        ),
        "visualization_example": {
            "type": "CHART",
            "chart_type": "column",
            "column_mapping": {"timestamp": "x", "value": "y"},
        },
        "production_refs": ["dola_transfers", "firm_liquidations", "dola_transfers_to_auction"],
    },
    {
        "id": "pg_stats_kpi",
        "category": "pg",
        "name": "Postgres KPI + time-series on stats tables",
        "summary": "Inverse Stats / Inverse Watch SQL for protocol health and alert monitoring.",
        "data_source_types": ["pg"],
        "frequency": "63 active Postgres queries",
        "patterns": [
            "Wide summary rows → multiple COUNTER visualizations (one column each)",
            "DATE_TRUNC / TO_CHAR for weekly ISO buckets (IYYY-IW)",
            "HTML links in cells: '<a href=\"./alerts/'||id||'\">Alert</a>'",
            "dola_health_* tables for collateral/liability tier breakdowns",
        ],
        "query_example": (
            "SELECT\n"
            "  COUNT(*) AS total_alerts,\n"
            "  COUNT(*) FILTER (WHERE last_triggered_at > NOW() - INTERVAL '7 days') AS triggered_7d\n"
            "FROM alerts\n"
            "WHERE org_id = 1"
        ),
        "visualization_example": {
            "type": "COUNTER",
            "name": "Total Alerts",
            "counter_column": "total_alerts",
        },
        "production_refs": ["dola_health_current", "stats_mcap", "alert_per_day_type", "Alert List"],
    },
    {
        "id": "dola_health_dashboard_layout",
        "category": "dashboard",
        "name": "Dola Health dashboard layout (KPI rows + tier charts)",
        "summary": "Production dashboard with 28 widgets — counters, tables, and paired charts.",
        "data_source_types": ["pg", "results"],
        "frequency": "Dashboard id 57 — 28 widgets",
        "patterns": [
            "KPI row: COUNTER widgets sizeX 1-2, sizeY 4 (Overall Collateral Ratio, Total Collateral)",
            "Detail row: TABLE sizeX 2 sizeY 8 beside CHART pairs sizeX 2 sizeY 8",
            "Repeat KPI+table+chart blocks per section (Lending, AMM) with row offsets",
            "Same query_id with multiple visualizations (agg, agg_lending, agg_amm)",
            "build_dashboard_from_spec roles: kpi for counters, half for side-by-side charts",
        ],
        "dashboard_layout_example": [
            {"role": "kpi", "visualization": "Overall Collateral Ratio", "sizeX": 1, "sizeY": 4},
            {"role": "kpi", "visualization": "DOLA Dominance Ratio", "sizeX": 1, "sizeY": 4},
            {"role": "kpi", "visualization": "Total Collateral", "sizeX": 2, "sizeY": 4},
            {"role": "kpi", "visualization": "Total Liability", "sizeX": 2, "sizeY": 4},
            {"role": "half", "visualization": "Overview Table"},
            {"role": "half", "visualization": "Collateral Amount per tier"},
            {"role": "half", "visualization": "Liability per Tier"},
        ],
        "production_refs": ["Dola Health dashboard", "dola_health_current_agg"],
    },
    {
        "id": "chart_column_mapping",
        "category": "visualization",
        "name": "Production CHART columnMapping patterns",
        "summary": "How real charts map columns — area/line/column/pie from 392 CHART visualizations.",
        "data_source_types": ["results", "pg", "python", "graphql", "evmstate"],
        "frequency": "area 148, line 140, column 64, pie 35",
        "patterns": [
            "Time series: {timestamp|day|block_time: x, metric: y}",
            "Multi-series: add contract_address or series column as series role",
            "Dual metric line: {time: x, market_cap: y, volume: y}",
            "Category column chart: {account: x, value: y}",
            "Pie breakdown: {account: x, value: y} with globalSeriesType pie",
            "Prefer omitting options — server auto-maps from validation.columns",
        ],
        "visualization_examples": [
            {
                "chart_type": "area",
                "column_mapping": {"timestamp": "x", "total_borrows": "y"},
                "query_pattern": "firm_borrows_repays_formated",
            },
            {
                "chart_type": "line",
                "column_mapping": {
                    "block_time": "x",
                    "value": "y",
                    "contract_address": "series",
                },
                "query_pattern": "treasury_balances",
            },
            {
                "chart_type": "pie",
                "column_mapping": {"account": "x", "value": "y"},
                "query_pattern": "vote_weight_formatted",
            },
        ],
        "production_refs": ["firm_borrows_repays_formated", "treasury_balances", "vote_weight_formatted"],
    },
    {
        "id": "counter_wide_row",
        "category": "visualization",
        "name": "COUNTER KPIs from a single wide summary row",
        "summary": "FiRM / Dola Health pattern — one Python or SQL row with many numeric columns.",
        "data_source_types": ["python", "pg", "results"],
        "frequency": "272 COUNTER visualizations",
        "patterns": [
            "Query returns ONE row with many metrics (total_debt_usd, total_collateral_usd, ...)",
            "Each COUNTER uses counterColName matching exact column name",
            "rowNumber: 1, targetRowNumber: 1 for single-row results",
            "create_multi_visualization_query builds several counters from one query",
            "Dashboard packs 4 counters per row (sizeX 3 in builder, sizeX 1-2 in production)",
        ],
        "query_example": (
            "SELECT\n"
            "  SUM(debt_usd) AS total_debt_usd_all_users,\n"
            "  SUM(collateral_usd) AS total_collateral_usd_all_users\n"
            "FROM firm_positions"
        ),
        "visualization_examples": [
            {"type": "COUNTER", "name": "Total Debt", "counter_column": "total_debt_usd_all_users"},
            {"type": "COUNTER", "name": "Total Collateral", "counter_column": "total_collateral_usd_all_users"},
        ],
        "production_refs": ["FiRM Positions", "dola_health_current_agg"],
    },
    {
        "id": "coingecko_endpoint",
        "category": "coingecko",
        "name": "CoinGecko YAML endpoint queries",
        "summary": "Lightweight market data fetches via endpoint: slugs.",
        "data_source_types": ["coingecko", "results"],
        "frequency": "Used with derived SQL for listing analysis",
        "patterns": [
            "endpoint: newly-listed for recent listings",
            "endpoint: coins-markets with params.ids for market cap rows",
            "Derived Query Results SQL formats nested JSON columns for charts",
        ],
        "query_example": "endpoint: newly-listed\n",
        "visualization_example": {
            "type": "TABLE",
            "name": "New Listings",
        },
        "production_refs": ["coingecko_new_listed", "new_listing_analysis"],
    },
    {
        "id": "dune_saved_query",
        "category": "dune",
        "name": "Dune API saved query execution",
        "summary": "Execute pre-built Dune SQL by query_id with parameters.",
        "data_source_types": ["dune"],
        "frequency": "4 active Dune queries",
        "patterns": [
            "query_id: <dune_query_id> — not raw SQL",
            "query_parameters: for Dune template variables",
            "performance: medium or large for heavy queries",
            "blockchains / addresses / date ranges as parameters",
        ],
        "query_example": (
            "query_id: 3673714\n"
            "query_parameters:\n"
            '  contract_address: "0x8aE125E8653821E851F12A49F7765db9a9ce7384"\n'
            '  blockchain: "optimism"\n'
            "performance: medium"
        ),
        "production_refs": ["dune_dola_opt_transfers", "graph_dola_multichain_filter_date_address"],
    },
]

INSTANCE_STATS: dict[str, Any] = {
    "source": "production_inverse_watch_instance",
    "note": "Read-only exploration — illustrative patterns only; resolve IDs in target workspace.",
    "totals": {
        "queries": 951,
        "active_queries": 537,
        "visualizations": 1644,
        "dashboards": "15+ active with 6-77 widgets each",
    },
    "top_data_source_types": [
        {"type": "results", "queries": 252},
        {"type": "pg", "queries": 63},
        {"type": "evmlogs", "queries": 52},
        {"type": "python", "queries": 42},
        {"type": "evmstate", "queries": 38},
        {"type": "graphql", "queries": 32},
    ],
    "top_chart_types": [
        {"type": "area", "count": 148},
        {"type": "line", "count": 140},
        {"type": "column", "count": 64},
        {"type": "pie", "count": 35},
    ],
    "data_sources_seen": [
        "pg", "results", "python", "evmlogs", "evmstate", "graphql", "json",
        "coingecko", "dune", "google_spreadsheets", "csv", "evmtransactions",
    ],
}


def list_instance_examples(
    query: Optional[str] = None,
    category: Optional[str] = None,
) -> dict[str, Any]:
    items: list[dict[str, Any]] = []
    needle = (query or "").strip().lower()
    cat = (category or "").strip().lower()

    for example in INSTANCE_EXAMPLES:
        if cat and example.get("category", "").lower() != cat:
            continue
        haystack = " ".join(
            [
                example["id"],
                example.get("category", ""),
                example["name"],
                example["summary"],
                " ".join(example.get("patterns") or []),
                " ".join(example.get("data_source_types") or []),
                " ".join(example.get("production_refs") or []),
            ]
        ).lower()
        if needle and needle not in haystack:
            continue
        items.append(
            {
                "id": example["id"],
                "category": example.get("category"),
                "name": example["name"],
                "summary": example["summary"],
                "data_source_types": example.get("data_source_types"),
                "patterns": example.get("patterns"),
                "frequency": example.get("frequency"),
            }
        )

    return {
        "examples": items,
        "count": len(items),
        "stats": INSTANCE_STATS,
        "categories": sorted({e.get("category", "") for e in INSTANCE_EXAMPLES if e.get("category")}),
        "hint": "Call get_instance_example(id) for query text, viz mappings, and layout snippets.",
    }


def get_instance_example(example_id: str) -> dict[str, Any]:
    example_id = (example_id or "").strip().lower()
    for example in INSTANCE_EXAMPLES:
        if example["id"] == example_id:
            return {
                "id": example["id"],
                "category": example.get("category"),
                "name": example["name"],
                "summary": example["summary"],
                "data_source_types": example.get("data_source_types"),
                "patterns": example.get("patterns"),
                "frequency": example.get("frequency"),
                "query_example": example.get("query_example"),
                "visualization_example": example.get("visualization_example"),
                "visualization_examples": example.get("visualization_examples"),
                "dashboard_layout_example": example.get("dashboard_layout_example"),
                "production_refs": example.get("production_refs"),
                "usage": (
                    "Adapt to the target workspace: list_data_sources for IDs, run_query to "
                    "validate columns, then create_query / create_visualization or "
                    "build_dashboard_from_spec. Child query IDs in query_{id} snippets are "
                    "examples — substitute real IDs from the current org."
                ),
            }
    known = [e["id"] for e in INSTANCE_EXAMPLES]
    return {
        "error": f"Unknown instance example {example_id!r}.",
        "known_ids": known,
        "stats": INSTANCE_STATS,
    }
