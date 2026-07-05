"""DefiLlama REST API query runner.

Queries are written as YAML, e.g.

    endpoint: protocol
    protocol: aave

    endpoint: prices-current
    coins: coingecko:ethereum,ethereum:0x...

The runner calls the DefiLlama free or Pro API and flattens responses into
Rewatch-style ``{rows, columns}``.
"""
import logging

from rewatch.query_runner import (
    TYPE_BOOLEAN,
    TYPE_DATETIME,
    TYPE_FLOAT,
    TYPE_INTEGER,
    TYPE_STRING,
    BaseHTTPQueryRunner,
    register,
)
from rewatch.query_runner.coingecko import (
    QueryParseError,
    parse_coingecko_response,
    parse_query,
)
logger = logging.getLogger(__name__)

FREE_BASE_URL = "https://api.llama.fi"
PRO_BASE_URL = "https://pro-api.llama.fi"

# Each entry drives both ``get_schema()`` and ``run_query()``.
# ``slug`` is the YAML ``endpoint`` value (kebab-case).
DEFILLAMA_ENDPOINTS = [
    # TVL
    {
        "category": "tvl",
        "slug": "protocols",
        "free_path": "protocols",
        "pro_path": "api/protocols",
        "description": "List all protocols with TVL",
        "path_params": [],
    },
    {
        "category": "tvl",
        "slug": "protocol",
        "free_path": "protocol/{protocol}",
        "pro_path": "api/protocol/{protocol}",
        "description": "Historical TVL for a protocol",
        "path_params": [{"name": "protocol", "type": TYPE_STRING, "example": "aave"}],
    },
    {
        "category": "tvl",
        "slug": "tvl",
        "free_path": "tvl/{protocol}",
        "pro_path": "api/tvl/{protocol}",
        "description": "Current TVL for a protocol (simplified)",
        "path_params": [{"name": "protocol", "type": TYPE_STRING, "example": "aave"}],
    },
    {
        "category": "tvl",
        "slug": "historical-chain-tvl",
        "free_path": "v2/historicalChainTvl",
        "pro_path": "api/v2/historicalChainTvl",
        "description": "Historical TVL across all chains",
        "path_params": [],
    },
    {
        "category": "tvl",
        "slug": "historical-chain-tvl-chain",
        "free_path": "v2/historicalChainTvl/{chain}",
        "pro_path": "api/v2/historicalChainTvl/{chain}",
        "description": "Historical TVL for a single chain",
        "path_params": [{"name": "chain", "type": TYPE_STRING, "example": "Ethereum"}],
    },
    {
        "category": "tvl",
        "slug": "chains",
        "free_path": "v2/chains",
        "pro_path": "api/v2/chains",
        "description": "Current TVL of all chains",
        "path_params": [],
    },
    {
        "category": "tvl",
        "slug": "token-protocols",
        "free_path": None,
        "pro_path": "api/tokenProtocols/{symbol}",
        "description": "Token usage across protocols (Pro)",
        "path_params": [{"name": "symbol", "type": TYPE_STRING, "example": "usdt"}],
        "pro_only": True,
    },
    {
        "category": "tvl",
        "slug": "inflows",
        "free_path": None,
        "pro_path": "api/inflows/{protocol}/{timestamp}",
        "description": "Protocol inflows/outflows at a date (Pro)",
        "path_params": [
            {"name": "protocol", "type": TYPE_STRING, "example": "compound-v3"},
            {"name": "timestamp", "type": TYPE_INTEGER, "example": "1767139200"},
        ],
        "pro_only": True,
    },
    {
        "category": "tvl",
        "slug": "chain-assets",
        "free_path": None,
        "pro_path": "api/chainAssets",
        "description": "Assets of all chains (Pro)",
        "path_params": [],
        "pro_only": True,
    },
    # Coins & prices
    {
        "category": "coins",
        "slug": "prices-current",
        "free_path": "prices/current/{coins}",
        "pro_path": "coins/prices/current/{coins}",
        "description": "Current token prices by contract address",
        "path_params": [{"name": "coins", "type": TYPE_STRING, "example": "coingecko:ethereum"}],
    },
    {
        "category": "coins",
        "slug": "prices-historical",
        "free_path": "prices/historical/{timestamp}/{coins}",
        "pro_path": "coins/prices/historical/{timestamp}/{coins}",
        "description": "Historical token prices at a timestamp",
        "path_params": [
            {"name": "timestamp", "type": TYPE_INTEGER, "example": "1667193600"},
            {"name": "coins", "type": TYPE_STRING, "example": "coingecko:ethereum"},
        ],
    },
    {
        "category": "coins",
        "slug": "batch-historical",
        "free_path": "batchHistorical",
        "pro_path": "coins/batchHistorical",
        "description": "Batch historical prices (POST body in params)",
        "path_params": [],
        "http_method": "post",
    },
    {
        "category": "coins",
        "slug": "chart",
        "free_path": "chart/{coins}",
        "pro_path": "coins/chart/{coins}",
        "description": "Token prices at regular intervals",
        "path_params": [{"name": "coins", "type": TYPE_STRING, "example": "coingecko:ethereum"}],
    },
    {
        "category": "coins",
        "slug": "percentage",
        "free_path": "percentage/{coins}",
        "pro_path": "coins/percentage/{coins}",
        "description": "Percentage price change over time",
        "path_params": [{"name": "coins", "type": TYPE_STRING, "example": "coingecko:ethereum"}],
    },
    {
        "category": "coins",
        "slug": "prices-first",
        "free_path": "prices/first/{coins}",
        "pro_path": "coins/prices/first/{coins}",
        "description": "Earliest price record for tokens",
        "path_params": [{"name": "coins", "type": TYPE_STRING, "example": "coingecko:ethereum"}],
    },
    {
        "category": "coins",
        "slug": "block",
        "free_path": "block/{chain}/{timestamp}",
        "pro_path": "coins/block/{chain}/{timestamp}",
        "description": "Closest block to a timestamp",
        "path_params": [
            {"name": "chain", "type": TYPE_STRING, "example": "ethereum"},
            {"name": "timestamp", "type": TYPE_INTEGER, "example": "1667193600"},
        ],
    },
    # Stablecoins
    {
        "category": "stablecoins",
        "slug": "stablecoins",
        "free_path": "stablecoins",
        "pro_path": "stablecoins/stablecoins",
        "description": "List all stablecoins with circulating amounts",
        "path_params": [],
    },
    {
        "category": "stablecoins",
        "slug": "stablecoincharts-all",
        "free_path": "stablecoincharts/all",
        "pro_path": "stablecoins/stablecoincharts/all",
        "description": "Historical mcap of all stablecoins",
        "path_params": [],
    },
    {
        "category": "stablecoins",
        "slug": "stablecoincharts-chain",
        "free_path": "stablecoincharts/{chain}",
        "pro_path": "stablecoins/stablecoincharts/{chain}",
        "description": "Historical stablecoin mcap on a chain",
        "path_params": [{"name": "chain", "type": TYPE_STRING, "example": "Ethereum"}],
    },
    {
        "category": "stablecoins",
        "slug": "stablecoin",
        "free_path": "stablecoin/{asset}",
        "pro_path": "stablecoins/stablecoin/{asset}",
        "description": "Historical mcap and chain distribution for a stablecoin",
        "path_params": [{"name": "asset", "type": TYPE_STRING, "example": "1"}],
    },
    {
        "category": "stablecoins",
        "slug": "stablecoinchains",
        "free_path": "stablecoinchains",
        "pro_path": "stablecoins/stablecoinchains",
        "description": "Stablecoin mcap sum per chain",
        "path_params": [],
    },
    {
        "category": "stablecoins",
        "slug": "stablecoinprices",
        "free_path": "stablecoinprices",
        "pro_path": "stablecoins/stablecoinprices",
        "description": "Historical prices of all stablecoins",
        "path_params": [],
    },
    {
        "category": "stablecoins",
        "slug": "stablecoindominance",
        "free_path": None,
        "pro_path": "stablecoins/stablecoindominance/{chain}",
        "description": "Stablecoin dominance per chain (Pro)",
        "path_params": [{"name": "chain", "type": TYPE_STRING, "example": "Ethereum"}],
        "pro_only": True,
    },
    # Yields
    {
        "category": "yields",
        "slug": "pools",
        "free_path": "pools",
        "pro_path": "yields/pools",
        "description": "Latest data for all yield pools",
        "path_params": [],
    },
    {
        "category": "yields",
        "slug": "pool-chart",
        "free_path": "chart/{pool}",
        "pro_path": "yields/chart/{pool}",
        "description": "Historical APY and TVL for a pool",
        "path_params": [{"name": "pool", "type": TYPE_STRING, "example": "pool-id"}],
    },
    {
        "category": "yields",
        "slug": "pools-borrow",
        "free_path": None,
        "pro_path": "yields/poolsBorrow",
        "description": "Borrow costs APY from lending markets (Pro)",
        "path_params": [],
        "pro_only": True,
    },
    {
        "category": "yields",
        "slug": "perps",
        "free_path": None,
        "pro_path": "yields/perps",
        "description": "Perp funding rates and open interest (Pro)",
        "path_params": [],
        "pro_only": True,
    },
    {
        "category": "yields",
        "slug": "lsd-rates",
        "free_path": None,
        "pro_path": "yields/lsdRates",
        "description": "LSD APY rates (Pro)",
        "path_params": [],
        "pro_only": True,
    },
    # DEX volumes
    {
        "category": "dex",
        "slug": "overview-dexs",
        "free_path": "overview/dexs",
        "pro_path": "api/overview/dexs",
        "description": "DEX volume overview",
        "path_params": [],
    },
    {
        "category": "dex",
        "slug": "overview-dexs-chain",
        "free_path": "overview/dexs/{chain}",
        "pro_path": "api/overview/dexs/{chain}",
        "description": "DEX volume overview for a chain",
        "path_params": [{"name": "chain", "type": TYPE_STRING, "example": "ethereum"}],
    },
    {
        "category": "dex",
        "slug": "summary-dexs",
        "free_path": "summary/dexs/{protocol}",
        "pro_path": "api/summary/dexs/{protocol}",
        "description": "DEX volume summary for a protocol",
        "path_params": [{"name": "protocol", "type": TYPE_STRING, "example": "uniswap"}],
    },
    {
        "category": "dex",
        "slug": "overview-options",
        "free_path": "overview/options",
        "pro_path": "api/overview/options",
        "description": "Options DEX volume overview",
        "path_params": [],
    },
    {
        "category": "dex",
        "slug": "overview-options-chain",
        "free_path": "overview/options/{chain}",
        "pro_path": "api/overview/options/{chain}",
        "description": "Options DEX volume overview for a chain",
        "path_params": [{"name": "chain", "type": TYPE_STRING, "example": "ethereum"}],
    },
    {
        "category": "dex",
        "slug": "summary-options",
        "free_path": "summary/options/{protocol}",
        "pro_path": "api/summary/options/{protocol}",
        "description": "Options DEX volume summary",
        "path_params": [{"name": "protocol", "type": TYPE_STRING, "example": "derive"}],
    },
    {
        "category": "dex",
        "slug": "overview-open-interest",
        "free_path": "overview/open-interest",
        "pro_path": "api/overview/open-interest",
        "description": "Open interest DEX overview",
        "path_params": [],
    },
    # Fees & revenue
    {
        "category": "fees",
        "slug": "overview-fees",
        "free_path": "overview/fees",
        "pro_path": "api/overview/fees",
        "description": "Protocol fees and revenue overview",
        "path_params": [],
    },
    {
        "category": "fees",
        "slug": "overview-fees-chain",
        "free_path": "overview/fees/{chain}",
        "pro_path": "api/overview/fees/{chain}",
        "description": "Fees and revenue overview for a chain",
        "path_params": [{"name": "chain", "type": TYPE_STRING, "example": "ethereum"}],
    },
    {
        "category": "fees",
        "slug": "summary-fees",
        "free_path": "summary/fees/{protocol}",
        "pro_path": "api/summary/fees/{protocol}",
        "description": "Fees and revenue summary for a protocol",
        "path_params": [{"name": "protocol", "type": TYPE_STRING, "example": "aave"}],
    },
    # Protocol analytics (Pro)
    {
        "category": "analytics",
        "slug": "categories",
        "free_path": None,
        "pro_path": "api/categories",
        "description": "Protocol categories overview (Pro)",
        "path_params": [],
        "pro_only": True,
    },
    {
        "category": "analytics",
        "slug": "forks",
        "free_path": None,
        "pro_path": "api/forks",
        "description": "Protocol forks overview (Pro)",
        "path_params": [],
        "pro_only": True,
    },
    {
        "category": "analytics",
        "slug": "oracles",
        "free_path": None,
        "pro_path": "api/oracles",
        "description": "Oracle usage overview (Pro)",
        "path_params": [],
        "pro_only": True,
    },
    {
        "category": "analytics",
        "slug": "hacks",
        "free_path": None,
        "pro_path": "api/hacks",
        "description": "DeFi hacks dashboard (Pro)",
        "path_params": [],
        "pro_only": True,
    },
    {
        "category": "analytics",
        "slug": "raises",
        "free_path": None,
        "pro_path": "api/raises",
        "description": "Protocol raises dashboard (Pro)",
        "path_params": [],
        "pro_only": True,
    },
    {
        "category": "analytics",
        "slug": "treasuries",
        "free_path": None,
        "pro_path": "api/treasuries",
        "description": "Protocol treasuries (Pro)",
        "path_params": [],
        "pro_only": True,
    },
    {
        "category": "analytics",
        "slug": "entities",
        "free_path": None,
        "pro_path": "api/entities",
        "description": "Protocol entities list (Pro)",
        "path_params": [],
        "pro_only": True,
    },
    {
        "category": "analytics",
        "slug": "emissions",
        "free_path": None,
        "pro_path": "api/emissions",
        "description": "Token unlock schedules (Pro)",
        "path_params": [],
        "pro_only": True,
    },
    {
        "category": "analytics",
        "slug": "emission",
        "free_path": None,
        "pro_path": "api/emission/{protocol}",
        "description": "Unlock data for a token/protocol (Pro)",
        "path_params": [{"name": "protocol", "type": TYPE_STRING, "example": "hyperliquid"}],
        "pro_only": True,
    },
    # Bridges (Pro)
    {
        "category": "bridges",
        "slug": "bridges",
        "free_path": None,
        "pro_path": "bridges/bridges",
        "description": "List all bridges (Pro)",
        "path_params": [],
        "pro_only": True,
    },
    {
        "category": "bridges",
        "slug": "bridge",
        "free_path": None,
        "pro_path": "bridges/bridge/{id}",
        "description": "Bridge details (Pro)",
        "path_params": [{"name": "id", "type": TYPE_STRING, "example": "1"}],
        "pro_only": True,
    },
    {
        "category": "bridges",
        "slug": "bridge-volume",
        "free_path": None,
        "pro_path": "bridges/bridgevolume/{chain}",
        "description": "Bridge volume on a chain (Pro)",
        "path_params": [{"name": "chain", "type": TYPE_STRING, "example": "ethereum"}],
        "pro_only": True,
    },
    # ETFs (Pro)
    {
        "category": "etfs",
        "slug": "etfs-snapshot",
        "free_path": None,
        "pro_path": "etfs/snapshot",
        "description": "ETF metrics snapshot (Pro)",
        "path_params": [],
        "pro_only": True,
    },
    {
        "category": "etfs",
        "slug": "etfs-flows",
        "free_path": None,
        "pro_path": "etfs/flows",
        "description": "ETF asset-level flows (Pro)",
        "path_params": [],
        "pro_only": True,
    },
]

ENDPOINT_BY_SLUG = {entry["slug"]: entry for entry in DEFILLAMA_ENDPOINTS}


def _sample_query(entry):
    lines = ["endpoint: {0}".format(entry["slug"])]
    for param in entry.get("path_params", []):
        if param.get("example"):
            lines.append("{0}: {1}".format(param["name"], param["example"]))
    return "\n".join(lines) + "\n"


def _schema_for_endpoint(entry):
    pro_label = " (Pro)" if entry.get("pro_only") else ""
    name = "{0}.{1}".format(entry["category"], entry["slug"])
    columns = []
    for param in entry.get("path_params", []):
        example = param.get("example", "")
        columns.append(
            {
                "name": param["name"],
                "type": param.get("type", TYPE_STRING),
                "description": "Path parameter",
                "insertValue": "{0}: {1}\n".format(param["name"], example) if example else "{0}: \n".format(param["name"]),
            }
        )
    columns.append(
        {
            "name": "params",
            "type": TYPE_STRING,
            "description": "Optional query-string parameters (YAML mapping under params:)",
            "insertValue": "params:\n  \n",
        }
    )
    return {
        "name": name,
        "displayName": entry["slug"] + pro_label,
        "description": entry["description"],
        "insertValue": _sample_query(entry),
        "columns": columns,
    }


def _resolve_path(path_template, query_config):
    path = path_template
    for key in [part.strip("{}") for part in path.split("/") if part.startswith("{") and part.endswith("}")]:
        value = query_config.get(key)
        if value is None and query_config.get("params"):
            value = query_config["params"].get(key)
        if value is None:
            raise QueryParseError("Missing required path parameter '{0}'.".format(key))
        path = path.replace("{{{0}}}".format(key), str(value))
    return path


class DefiLlama(BaseHTTPQueryRunner):
    """DefiLlama DeFi analytics API query runner."""

    requires_url = False

    @classmethod
    def name(cls):
        return "DefiLlama"

    @classmethod
    def type(cls):
        return "defillama"

    @classmethod
    def configuration_schema(cls):
        return {
            "type": "object",
            "properties": {
                "api_key": {
                    "type": "string",
                    "title": "Pro API Key (Optional)",
                    "description": "DefiLlama Pro API key for higher rate limits and exclusive endpoints",
                },
                "base_url": {
                    "type": "string",
                    "title": "Base URL",
                    "default": FREE_BASE_URL,
                    "description": "DefiLlama API base URL (free or pro)",
                },
                "timeout": {
                    "type": "integer",
                    "title": "Request Timeout (seconds)",
                    "default": 30,
                },
            },
            "secret": ["api_key"],
            "order": ["base_url", "api_key", "timeout"],
        }

    def __init__(self, configuration):
        super(DefiLlama, self).__init__(configuration)
        self.syntax = "yaml"
        self.api_key = self.configuration.get("api_key")
        self.base_url = (self.configuration.get("base_url") or FREE_BASE_URL).rstrip("/")
        self.timeout = self.configuration.get("timeout", 30)
        self.use_pro = bool(self.api_key) or "pro-api.llama.fi" in self.base_url

    def test_connection(self):
        entry = ENDPOINT_BY_SLUG["protocols"]
        url = self._build_url(entry)
        response, error = self.get_response(url, timeout=self.timeout)
        if error:
            raise Exception(error)
        if response.status_code != 200:
            raise Exception("API returned status code {0}".format(response.status_code))

    def _build_url(self, entry):
        path_template = entry["pro_path"] if self.use_pro else entry.get("free_path")
        if not path_template:
            raise QueryParseError(
                "Endpoint '{0}' requires a Pro API key.".format(entry["slug"])
            )
        if self.use_pro:
            if self.api_key:
                return "{0}/{1}/{2}".format(PRO_BASE_URL, self.api_key, path_template)
            return "{0}/{1}".format(self.base_url, path_template)
        return "{0}/{1}".format(self.base_url, path_template)

    def get_schema(self, get_stats=False):
        schema = []
        for entry in DEFILLAMA_ENDPOINTS:
            if entry.get("pro_only") and not self.use_pro:
                continue
            if not self.use_pro and not entry.get("free_path"):
                continue
            schema.append(_schema_for_endpoint(entry))
        return schema

    def run_query(self, query, user):
        try:
            query_config = parse_query(query)
            if not isinstance(query_config, dict):
                raise QueryParseError("Query should be a YAML object describing the DefiLlama API request.")

            endpoint_slug = query_config.get("endpoint")
            if not endpoint_slug:
                raise QueryParseError("Missing required field 'endpoint'.")

            entry = ENDPOINT_BY_SLUG.get(endpoint_slug)
            if not entry:
                raise QueryParseError(
                    "Unknown endpoint '{0}'. Use get_schema to browse available endpoints.".format(endpoint_slug)
                )

            path_template = entry["pro_path"] if self.use_pro else entry.get("free_path")
            if not path_template:
                raise QueryParseError("Endpoint '{0}' requires a Pro API key.".format(endpoint_slug))

            path = _resolve_path(path_template, query_config)
            if self.use_pro and self.api_key:
                url = "{0}/{1}/{2}".format(PRO_BASE_URL, self.api_key, path)
            elif self.use_pro:
                url = "{0}/{1}".format(self.base_url, path)
            else:
                url = "{0}/{1}".format(self.base_url, path)

            params = dict(query_config.get("params") or {})
            http_method = entry.get("http_method", "get")
            request_kwargs = {"timeout": self.timeout}
            if http_method == "post":
                request_kwargs["json"] = params
                params = None

            response, error = self.get_response(url, params=params, http_method=http_method, **request_kwargs)
            if error:
                return None, "API request failed: {0}".format(error)
            if response.status_code != 200:
                return None, "API returned status code {0}".format(response.status_code)

            try:
                data = response.json()
            except ValueError as e:
                return None, "Failed to parse JSON response: {0}".format(e)

            # Many DefiLlama responses wrap rows under ``data`` or return arrays directly.
            if isinstance(data, dict) and "data" in data and isinstance(data["data"], list):
                rows_data = data["data"]
            elif isinstance(data, dict) and "coins" in data:
                rows_data = data
            else:
                rows_data = data

            parsed = parse_coingecko_response(rows_data, "generic")
            return parsed, None

        except QueryParseError as e:
            return None, str(e)
        except Exception as e:
            logger.exception("Error running DefiLlama query")
            return None, "Query execution failed: {0}".format(e)


register(DefiLlama)
