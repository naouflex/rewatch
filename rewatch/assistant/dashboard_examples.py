"""Curated dashboard build examples from scripts/create_*_dashboard.py."""

from __future__ import annotations

from typing import Any, Optional

DASHBOARD_EXAMPLES: list[dict[str, Any]] = [
    {
        "id": "ethereum_defi",
        "name": "Ethereum DeFi Ecosystem",
        "summary": "DefiLlama + Coingecko YAML APIs with derived SQL on cached results.",
        "data_source_types": ["coingecko", "defillama", "query_results"],
        "patterns": [
            "Base queries use `key` for cached_query references",
            "Derived queries use {{cached_query.KEY}} on Query Results source",
            "KPI counters + area/line charts + pie charts in one build_dashboard_from_spec call",
        ],
        "query_count": 12,
        "widget_count": 25,
        "spec_snippet": {
            "name": "Ethereum DeFi Ecosystem",
            "queries": [
                {
                    "key": "protocols",
                    "name": "DeFi - All Protocols",
                    "data_source_id": 10,
                    "query": "endpoint: protocols",
                    "visualizations": [],
                },
                {
                    "name": "DeFi - ETH TVL History",
                    "data_source_id": 10,
                    "query": "endpoint: historical-chain-tvl-chain\nchain: Ethereum",
                    "visualizations": [
                        {
                            "type": "CHART",
                            "name": "ETH TVL History",
                            "chart_type": "area",
                            "column_mapping": {"date": "x", "tvl": "y"},
                        }
                    ],
                },
            ],
            "derived": [
                {
                    "name": "DeFi - Top Protocols",
                    "query": (
                        "SELECT name, category, ROUND(chainTvls_Ethereum / 1e9, 2) AS eth_tvl_b "
                        "FROM {{cached_query.protocols}} "
                        "WHERE chainTvls_Ethereum > 1e6 ORDER BY chainTvls_Ethereum DESC LIMIT 20"
                    ),
                    "visualizations": [{"type": "TABLE", "name": "Top ETH Protocols"}],
                }
            ],
            "widgets": [
                {"text": "# Ethereum DeFi Ecosystem"},
                {"visualization": "ETH TVL History", "role": "full"},
                {"visualization": "Top ETH Protocols"},
            ],
        },
    },
    {
        "id": "montpellier_weather",
        "name": "Montpellier Weather",
        "summary": "Live Open-Meteo forecast + air quality via Python data source queries.",
        "data_source_types": ["python"],
        "patterns": [
            "Python query fetches external HTTP APIs and returns rows",
            "Multiple CHART types for temperature, rain, wind, AQI",
            "Section markdown headers between widget groups",
        ],
        "query_count": 8,
        "widget_count": 20,
        "spec_snippet": {
            "name": "Montpellier Weather",
            "queries": [
                {
                    "name": "Weather - Current Conditions",
                    "data_source_id": 4,
                    "query": "# Python: fetch Open-Meteo current + hourly forecast for lat/lon",
                    "visualizations": [
                        {"type": "COUNTER", "name": "Temperature", "counter_column": "temperature"},
                        {"type": "COUNTER", "name": "Feels Like", "counter_column": "feels_like"},
                    ],
                }
            ],
            "widgets": [
                {"text": "# Montpellier Weather"},
                {"visualization": "Temperature", "role": "kpi"},
                {"visualization": "Feels Like", "role": "kpi"},
            ],
        },
    },
    {
        "id": "montpellier_airport",
        "name": "Montpellier Airport (LFMT/MPL)",
        "summary": "FlightAware AeroAPI via one Python query + derived SQL for boards and charts.",
        "data_source_types": ["python", "query_results"],
        "patterns": [
            "Single Python query minimizes external API quota",
            "Derived SQL splits arrivals/departures/history from cached_query table",
            "TABLE widgets for flight boards, CHART for delay trends",
        ],
        "query_count": 6,
        "widget_count": 18,
        "spec_snippet": {
            "name": "Montpellier Airport",
            "queries": [
                {
                    "key": "flights",
                    "name": "Airport - All Flights",
                    "data_source_id": 4,
                    "query": "# Python: AeroAPI fetch for LFMT/MPL",
                    "visualizations": [],
                }
            ],
            "derived": [
                {
                    "name": "Airport - Arrivals Board",
                    "query": (
                        "SELECT * FROM {{cached_query.flights}} "
                        "WHERE direction = 'arrival' ORDER BY scheduled_time LIMIT 20"
                    ),
                    "visualizations": [{"type": "TABLE", "name": "Arrivals"}],
                }
            ],
            "widgets": [
                {"text": "# Montpellier Airport"},
                {"visualization": "Arrivals", "role": "half"},
            ],
        },
    },
    {
        "id": "hypertrader_user",
        "name": "Hypertrader User Activity",
        "summary": "SQL dashboard on application Postgres tables for one user's activity KPIs.",
        "data_source_types": ["pg"],
        "patterns": [
            "Wide summary row with multiple COUNTER visualizations",
            "Time-series CHARTs for events and messages",
            "Text section headers — always set widget text, never null",
        ],
        "query_count": 10,
        "widget_count": 22,
        "spec_snippet": {
            "name": "Hypertrader User Activity",
            "queries": [
                {
                    "name": "Hypertrader User - Activity Summary",
                    "data_source_id": 12,
                    "query": "SELECT COUNT(*) AS total_backtests, ... FROM saved_backtests WHERE user_id = 1",
                    "visualizations": [
                        {"type": "COUNTER", "name": "Backtests", "counter_column": "total_backtests"},
                    ],
                }
            ],
            "widgets": [
                {"text": "# Hypertrader User Activity"},
                {"visualization": "Backtests", "role": "kpi"},
            ],
        },
    },
    {
        "id": "sniffer_audit",
        "name": "Sniffer Token Audit",
        "summary": "SQL dashboard for token audit metrics with counters and category charts.",
        "data_source_types": ["pg"],
        "patterns": [
            "Multiple related SQL queries on same data source",
            "COUNTER row + CHART breakdowns + TABLE detail",
        ],
        "query_count": 8,
        "widget_count": 16,
        "spec_snippet": {
            "name": "Sniffer Token Audit",
            "queries": [
                {
                    "name": "Sniffer - Summary",
                    "data_source_id": 14,
                    "query": "SELECT COUNT(*) AS tokens_audited, ... FROM audits",
                    "visualizations": [
                        {"type": "COUNTER", "name": "Tokens Audited", "counter_column": "tokens_audited"},
                    ],
                }
            ],
            "widgets": [{"text": "# Sniffer Audit Overview"}, {"visualization": "Tokens Audited", "role": "kpi"}],
        },
    },
    {
        "id": "viz_demo",
        "name": "Visualization Gallery",
        "summary": "Exercises all ECharts series types and specialized viz types (MAP, SANKEY, etc.).",
        "data_source_types": ["pg"],
        "patterns": [
            "One query per visualization type with minimal seed SQL",
            "Reference for CHART globalSeriesType values and column shapes",
            "Use list_dashboard_examples(id='viz_demo') before unfamiliar viz types",
        ],
        "query_count": 15,
        "widget_count": 15,
        "spec_snippet": {
            "name": "Visualization Gallery (ECharts + Nivo)",
            "queries": [
                {
                    "name": "Viz Demo - Time Series",
                    "data_source_id": 2,
                    "query": "SELECT d::date AS date, s AS series, v AS value FROM ... ORDER BY 1, 2",
                    "visualizations": [
                        {"type": "CHART", "name": "Multi-series Line", "chart_type": "line"}
                    ],
                }
            ],
            "widgets": [{"visualization": "Multi-series Line", "role": "half"}],
        },
    },
]


def list_dashboard_examples(query: Optional[str] = None) -> dict[str, Any]:
    items: list[dict[str, Any]] = []
    needle = (query or "").strip().lower()
    for example in DASHBOARD_EXAMPLES:
        haystack = " ".join(
            [
                example["id"],
                example["name"],
                example["summary"],
                " ".join(example.get("patterns") or []),
                " ".join(example.get("data_source_types") or []),
            ]
        ).lower()
        if needle and needle not in haystack:
            continue
        items.append(
            {
                "id": example["id"],
                "name": example["name"],
                "summary": example["summary"],
                "data_source_types": example.get("data_source_types"),
                "patterns": example.get("patterns"),
                "query_count": example.get("query_count"),
                "widget_count": example.get("widget_count"),
            }
        )
    return {
        "examples": items,
        "count": len(items),
        "hint": "Call get_dashboard_example(id) for a full build_dashboard_from_spec snippet.",
    }


def get_dashboard_example(example_id: str) -> dict[str, Any]:
    example_id = (example_id or "").strip().lower()
    for example in DASHBOARD_EXAMPLES:
        if example["id"] == example_id:
            return {
                "id": example["id"],
                "name": example["name"],
                "summary": example["summary"],
                "patterns": example.get("patterns"),
                "spec_snippet": example.get("spec_snippet"),
                "usage": (
                    "Adapt data_source_id values with list_data_sources, explore columns with run_query, "
                    "then pass an expanded spec to build_dashboard_from_spec."
                ),
            }
    known = [e["id"] for e in DASHBOARD_EXAMPLES]
    return {
        "error": f"Unknown dashboard example {example_id!r}.",
        "known_ids": known,
    }
