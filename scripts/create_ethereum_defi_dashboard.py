#!/usr/bin/env python3
"""Create Ethereum DeFi ecosystem dashboard from DefiLlama + Coingecko data.

Thin declarative spec on top of rewatch.assistant.dashboard_builder: base
queries hit the external APIs, derived queries aggregate their cached results
via {{cached_query.KEY}} placeholders on the Query Results data source.
"""

from __future__ import annotations

from dashboard_script_utils import build_and_report

DS_COINGECKO = 9
DS_DEFILLAMA = 10

ETH_CHART_COLORS = {
    "price": "#FF7230",
    "market_cap": "#7950F2",
    "volume": "#15AABF",
    "tvl": "#627EEA",
    "aave_tvl": "#12B886",
}


def counter(name: str, column: str, label: str = "") -> dict:
    return {"type": "COUNTER", "name": name, "counter_column": column, "counter_label": label}


def styled_chart(name: str, chart_type: str, mapping: dict, *, color: str, series_key: str) -> dict:
    """Single-series time chart with a fixed brand color."""
    return {
        "type": "CHART",
        "name": name,
        "options": {
            "globalSeriesType": chart_type,
            "columnMapping": mapping,
            "color_scheme": "Rewatch",
            "seriesOptions": {series_key: {"color": color, "type": chart_type}},
            "legend": {"enabled": False},
            "xAxis": {"type": "datetime", "labels": {"enabled": True}},
            "sortX": True,
        },
    }


def pie_chart(name: str, mapping: dict, color_scheme: str) -> dict:
    return {
        "type": "CHART",
        "name": name,
        "options": {
            "globalSeriesType": "pie",
            "columnMapping": mapping,
            "color_scheme": color_scheme,
            "showDataLabels": True,
            "legend": {"enabled": True, "placement": "right"},
        },
    }


QUERIES = [
    {
        "key": "eth_price",
        "name": "ETH DeFi - ETH Price",
        "description": "Current ETH price and market cap from Coingecko.",
        "data_source_id": DS_COINGECKO,
        "query": (
            "endpoint: coins-markets\n"
            "params:\n"
            "  vs_currency: usd\n"
            "  ids: ethereum\n"
            "  per_page: 1\n"
            "  sparkline: false\n"
            "  price_change_percentage: 24h"
        ),
        "visualizations": [
            counter("ETH Price", "current_price", "USD"),
            counter("ETH Market Cap", "market_cap", "USD"),
            counter("ETH 24h Change", "price_change_percentage_24h", "%"),
        ],
    },
    {
        "key": "eth_market",
        "name": "ETH DeFi - ETH Market 90d",
        "description": "ETH price, market cap, and volume over the last 90 days.",
        "data_source_id": DS_COINGECKO,
        "query": "endpoint: market-chart\ncoingeckoID: ethereum\nparams:\n  vs_currency: usd\n  days: 90",
        "visualizations": [
            styled_chart(
                "ETH Price 90d", "line", {"datetime": "x", "price": "y"},
                color=ETH_CHART_COLORS["price"], series_key="price",
            ),
            styled_chart(
                "ETH Market Cap 90d", "area", {"datetime": "x", "market_cap": "y"},
                color=ETH_CHART_COLORS["market_cap"], series_key="market_cap",
            ),
            styled_chart(
                "ETH Volume 90d", "column", {"datetime": "x", "volume": "y"},
                color=ETH_CHART_COLORS["volume"], series_key="volume",
            ),
        ],
    },
    {
        "key": "eth_tvl",
        "name": "ETH DeFi - ETH TVL History",
        "description": "Ethereum chain TVL history from DefiLlama.",
        "data_source_id": DS_DEFILLAMA,
        "query": "endpoint: historical-chain-tvl-chain\nchain: Ethereum",
        "visualizations": [
            styled_chart(
                "ETH TVL History", "area", {"datetime": "x", "tvl": "y"},
                color=ETH_CHART_COLORS["tvl"], series_key="tvl",
            ),
        ],
    },
    {
        "key": "dex_overview",
        "name": "ETH DeFi - DEX Overview",
        "description": "Ethereum DEX volume aggregates from DefiLlama.",
        "data_source_id": DS_DEFILLAMA,
        "query": "endpoint: overview-dexs-chain\nchain: ethereum",
        "visualizations": [
            counter("DEX Vol 24h", "total24h", "USD"),
            counter("DEX Vol 7d", "total7d", "USD"),
            counter("DEX Vol 30d", "total30d", "USD"),
            counter("DEX Change 1d", "change_1d", "%"),
            counter("DEX Change 7d", "change_7d", "%"),
        ],
    },
    {
        "key": "fees_overview",
        "name": "ETH DeFi - Fees Overview",
        "description": "Ethereum protocol fees from DefiLlama.",
        "data_source_id": DS_DEFILLAMA,
        "query": "endpoint: overview-fees-chain\nchain: ethereum",
        "visualizations": [
            counter("Fees 24h", "total24h", "USD"),
            counter("Fees 7d", "total7d", "USD"),
            counter("Fees 30d", "total30d", "USD"),
            counter("Fees Change 1d", "change_1d", "%"),
            counter("Fees Change 7d", "change_7d", "%"),
        ],
    },
    {
        "key": "chains",
        "name": "ETH DeFi - All Chains",
        "description": "TVL across all blockchains from DefiLlama.",
        "data_source_id": DS_DEFILLAMA,
        "query": "endpoint: chains",
        "visualizations": [],
    },
    {
        "key": "protocols",
        "name": "ETH DeFi - All Protocols",
        "description": "All DeFi protocols with per-chain TVL from DefiLlama.",
        "data_source_id": DS_DEFILLAMA,
        "query": "endpoint: protocols",
        "visualizations": [],
    },
    {
        "key": "defi_tokens",
        "name": "ETH DeFi - DeFi Tokens",
        "description": "Top DeFi tokens by market cap from Coingecko.",
        "data_source_id": DS_COINGECKO,
        "query": (
            "endpoint: coins-markets\n"
            "params:\n"
            "  vs_currency: usd\n"
            "  category: decentralized-finance-defi\n"
            "  order: market_cap_desc\n"
            "  per_page: 25\n"
            "  page: 1\n"
            "  sparkline: false\n"
            "  price_change_percentage: 24h,7d"
        ),
        "visualizations": [{"type": "TABLE", "name": "DeFi Tokens"}],
    },
    {
        "key": "aave_tvl",
        "name": "ETH DeFi - Aave TVL History",
        "description": "Aave protocol TVL history from DefiLlama.",
        "data_source_id": DS_DEFILLAMA,
        "query": "endpoint: protocol\nprotocol: aave",
        "visualizations": [
            styled_chart(
                "Aave TVL History", "line", {"datetime": "x", "tvl": "y"},
                color=ETH_CHART_COLORS["aave_tvl"], series_key="tvl",
            ),
        ],
    },
]

DERIVED = [
    {
        "key": "latest_tvl",
        "name": "ETH DeFi - Latest ETH TVL",
        "description": "Most recent Ethereum chain TVL in billions.",
        "query": (
            "SELECT ROUND(tvl / 1e9, 2) AS eth_tvl_billions, datetime\n"
            "FROM {{cached_query.eth_tvl}}\n"
            "ORDER BY date DESC\n"
            "LIMIT 1"
        ),
        "visualizations": [counter("ETH TVL", "eth_tvl_billions", "USD B")],
    },
    {
        "key": "top_chains",
        "name": "ETH DeFi - Top Chains by TVL",
        "description": "Top blockchains ranked by total value locked.",
        "query": (
            "SELECT name, ROUND(tvl / 1e9, 2) AS tvl_billions\n"
            "FROM {{cached_query.chains}}\n"
            "WHERE tvl > 0\n"
            "ORDER BY tvl DESC\n"
            "LIMIT 12"
        ),
        "visualizations": [pie_chart("Top Chains by TVL", {"name": "x", "tvl_billions": "y"}, "Tableau 10")],
    },
    {
        "key": "top_protocols",
        "name": "ETH DeFi - Top ETH Protocols",
        "description": "Largest protocols by Ethereum TVL.",
        "query": (
            "SELECT name, category, symbol,\n"
            "  ROUND(chainTvls_Ethereum / 1e9, 2) AS eth_tvl_b,\n"
            "  ROUND(tvl / 1e9, 2) AS total_tvl_b,\n"
            "  ROUND(change_1d, 2) AS change_1d_pct,\n"
            "  ROUND(change_7d, 2) AS change_7d_pct\n"
            "FROM {{cached_query.protocols}}\n"
            "WHERE chainTvls_Ethereum > 1000000\n"
            "  AND category NOT IN ('CEX')\n"
            "ORDER BY chainTvls_Ethereum DESC\n"
            "LIMIT 20"
        ),
        "visualizations": [{"type": "TABLE", "name": "Top ETH Protocols"}],
    },
    {
        "key": "tvl_by_category",
        "name": "ETH DeFi - ETH TVL by Category",
        "description": "Ethereum TVL grouped by protocol category.",
        "query": (
            "SELECT category,\n"
            "  COUNT(*) AS protocols,\n"
            "  ROUND(SUM(chainTvls_Ethereum) / 1e9, 2) AS eth_tvl_b\n"
            "FROM {{cached_query.protocols}}\n"
            "WHERE chainTvls_Ethereum IS NOT NULL\n"
            "  AND chainTvls_Ethereum > 0\n"
            "  AND category NOT IN ('CEX')\n"
            "GROUP BY category\n"
            "ORDER BY eth_tvl_b DESC\n"
            "LIMIT 15"
        ),
        "visualizations": [
            pie_chart("ETH TVL by Category", {"category": "x", "eth_tvl_b": "y"}, "D3 Category 10")
        ],
    },
    {
        "key": "lending_protocols",
        "name": "ETH DeFi - Top Lending on ETH",
        "description": "Lending protocols ranked by Ethereum TVL.",
        "query": (
            "SELECT name, symbol,\n"
            "  ROUND(chainTvls_Ethereum / 1e9, 2) AS eth_tvl_b,\n"
            "  ROUND(change_7d, 2) AS change_7d_pct\n"
            "FROM {{cached_query.protocols}}\n"
            "WHERE category = 'Lending'\n"
            "  AND chainTvls_Ethereum > 0\n"
            "ORDER BY chainTvls_Ethereum DESC\n"
            "LIMIT 10"
        ),
        "visualizations": [pie_chart("Lending on Ethereum", {"name": "x", "eth_tvl_b": "y"}, "Rewatch")],
    },
]


def pos(col: int, row: int, size_x: int, size_y: int) -> dict:
    return {"col": col, "row": row, "sizeX": size_x, "sizeY": size_y}


WIDGETS = [
    {
        "text": "# Ethereum DeFi Ecosystem\n\nMarket pulse, TVL, DEX volume, fees, and protocol landscape — powered by DefiLlama and Coingecko.",
        "position": pos(0, 0, 12, 3),
    },
    {"text": "## Market Pulse", "position": pos(0, 3, 12, 2)},
    {"visualization": "ETH Price", "position": pos(0, 5, 3, 8)},
    {"visualization": "ETH TVL", "position": pos(3, 5, 3, 8)},
    {"visualization": "DEX Vol 24h", "position": pos(6, 5, 3, 8)},
    {"visualization": "Fees 24h", "position": pos(9, 5, 3, 8)},
    {"visualization": "ETH 24h Change", "position": pos(0, 13, 3, 8)},
    {"visualization": "ETH Market Cap", "position": pos(3, 13, 3, 8)},
    {"visualization": "DEX Change 1d", "position": pos(6, 13, 3, 8)},
    {"visualization": "Fees Change 1d", "position": pos(9, 13, 3, 8)},
    {"text": "## TVL & Market Trends", "position": pos(0, 21, 12, 2)},
    {"visualization": "ETH TVL History", "position": pos(0, 23, 12, 8)},
    {"visualization": "ETH Price 90d", "position": pos(0, 31, 6, 8)},
    {"visualization": "ETH Market Cap 90d", "position": pos(6, 31, 6, 8)},
    {"visualization": "ETH Volume 90d", "position": pos(0, 39, 12, 6)},
    {"visualization": "Top Chains by TVL", "position": pos(0, 45, 12, 8)},
    {"text": "## Protocol Landscape", "position": pos(0, 53, 12, 2)},
    {"visualization": "Top ETH Protocols", "position": pos(0, 55, 8, 8)},
    {"visualization": "ETH TVL by Category", "position": pos(8, 55, 4, 8)},
    {"visualization": "Lending on Ethereum", "position": pos(0, 63, 6, 8)},
    {"visualization": "Aave TVL History", "position": pos(6, 63, 6, 8)},
    {"text": "## Activity & Tokens", "position": pos(0, 71, 12, 2)},
    {"visualization": "DEX Vol 7d", "position": pos(0, 73, 3, 8)},
    {"visualization": "DEX Vol 30d", "position": pos(3, 73, 3, 8)},
    {"visualization": "DEX Change 7d", "position": pos(6, 73, 3, 8)},
    {"visualization": "Fees 7d", "position": pos(9, 73, 3, 8)},
    {"visualization": "Fees 30d", "position": pos(0, 81, 3, 8)},
    {"visualization": "Fees Change 7d", "position": pos(3, 81, 3, 8)},
    {"visualization": "DeFi Tokens", "position": pos(0, 89, 12, 8)},
]


if __name__ == "__main__":
    build_and_report(
        name="Ethereum DeFi Ecosystem",
        queries=QUERIES,
        derived=DERIVED,
        widgets=WIDGETS,
    )
