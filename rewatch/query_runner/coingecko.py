"""CoinGecko REST API query runner.

Queries are written as YAML, e.g.

    endpoint: market-chart
    coingeckoID: ethereum
    params:
      vs_currency: usd
      days: 30

The runner translates the YAML into a CoinGecko REST call and flattens the
response into Rewatch-style ``{rows, columns}``. Ported from inverse-watch.
"""
import datetime
import logging
import time

import yaml

from rewatch.query_runner import (
    TYPE_BOOLEAN,
    TYPE_DATETIME,
    TYPE_FLOAT,
    TYPE_INTEGER,
    TYPE_STRING,
    BaseHTTPQueryRunner,
    register,
)
from rewatch.utils import json_dumps

logger = logging.getLogger(__name__)


class QueryParseError(Exception):
    pass


def parse_query(query):
    query = query.strip()
    if query == "":
        raise QueryParseError("Query is empty.")
    try:
        return yaml.safe_load(query)
    except (yaml.YAMLError, ValueError) as e:
        raise QueryParseError(str(e))


TYPES_MAP = {
    str: TYPE_STRING,
    bytes: TYPE_STRING,
    int: TYPE_INTEGER,
    float: TYPE_FLOAT,
    bool: TYPE_BOOLEAN,
    datetime.datetime: TYPE_DATETIME,
}


def _get_type(value):
    return TYPES_MAP.get(type(value), TYPE_STRING)


def _get_column_by_name(columns, column_name):
    safe_column_name = column_name.replace(".", "_")
    for c in columns:
        if c.get("name") in (column_name, safe_column_name):
            return c
    return None


def add_column(columns, column_name, column_type, friendly_name=None):
    if _get_column_by_name(columns, column_name) is None:
        safe_column_name = column_name.replace(".", "_")
        columns.append(
            {
                "name": safe_column_name,
                "friendly_name": friendly_name or column_name,
                "type": column_type,
            }
        )


def flatten_dict(d, parent_key="", sep="."):
    items = []
    for k, v in d.items():
        new_key = "{0}{1}{2}".format(parent_key, sep, k) if parent_key else k
        if isinstance(v, dict):
            items.extend(flatten_dict(v, new_key, sep=sep).items())
        else:
            items.append((new_key, v))
    return dict(items)


def parse_coingecko_response(data, endpoint_type="simple_price"):
    rows = []
    columns = []

    if endpoint_type == "simple_price":
        for coin_id, price_data in data.items():
            row = {"coin_id": coin_id}
            add_column(columns, "coin_id", TYPE_STRING, "Coin ID")
            for currency, price in price_data.items():
                if isinstance(price, (int, float)):
                    row["price_{0}".format(currency)] = price
                    add_column(
                        columns,
                        "price_{0}".format(currency),
                        TYPE_FLOAT,
                        "Price ({0})".format(currency.upper()),
                    )
                else:
                    row[currency] = price
                    add_column(columns, currency, _get_type(price), currency.upper())
            rows.append(row)

    elif endpoint_type == "market_chart":
        for i, price_point in enumerate(data.get("prices", [])):
            timestamp, price = price_point
            row = {
                "timestamp": timestamp,
                "datetime": datetime.datetime.fromtimestamp(timestamp / 1000).isoformat(),
                "price": price,
            }
            if "market_caps" in data and i < len(data["market_caps"]):
                row["market_cap"] = data["market_caps"][i][1]
            if "total_volumes" in data and i < len(data["total_volumes"]):
                row["volume"] = data["total_volumes"][i][1]
            rows.append(row)
        if data.get("prices"):
            add_column(columns, "timestamp", TYPE_INTEGER, "Timestamp")
            add_column(columns, "datetime", TYPE_DATETIME, "Date Time")
            add_column(columns, "price", TYPE_FLOAT, "Price")
            if "market_caps" in data:
                add_column(columns, "market_cap", TYPE_FLOAT, "Market Cap")
            if "total_volumes" in data:
                add_column(columns, "volume", TYPE_FLOAT, "Volume")

    elif endpoint_type == "coin_detail":
        flattened = flatten_dict(data)
        row = {}
        for key, value in flattened.items():
            safe_key = key.replace(".", "_")
            row[safe_key] = value
            if key.startswith("market_data.current_price."):
                currency = key.split(".")[-1]
                add_column(columns, key, TYPE_FLOAT, "Current Price ({0})".format(currency.upper()))
            elif key.startswith("market_data."):
                field_name = key.replace("market_data.", "").replace("_", " ").title()
                column_type = (
                    TYPE_FLOAT
                    if any(x in key for x in ["price", "cap", "volume", "supply", "change", "high", "low", "ath", "atl"])
                    else _get_type(value)
                )
                add_column(columns, key, column_type, field_name)
            elif key.startswith("platforms."):
                platform_name = key.replace("platforms.", "")
                add_column(columns, key, TYPE_STRING, "Platform {0}".format(platform_name.title()))
            else:
                add_column(columns, key, _get_type(value), key.replace("_", " ").title())
        rows.append(row)

    elif endpoint_type in ("coins_list", "coins_list_platforms"):
        for coin in data:
            flattened = flatten_dict(coin)
            row = {}
            for key, value in flattened.items():
                safe_key = key.replace(".", "_")
                row[safe_key] = value
                if key == "platforms" and isinstance(value, dict):
                    for platform_name, contract_address in value.items():
                        platform_key = "platform_{0}".format(platform_name)
                        row[platform_key.replace(".", "_")] = contract_address
                        add_column(columns, platform_key, TYPE_STRING, "Platform {0}".format(platform_name.title()))
                else:
                    add_column(columns, key, _get_type(value), key.replace("_", " ").title())
            rows.append(row)

    elif endpoint_type == "coins_markets":
        float_fields = {
            "current_price",
            "market_cap",
            "market_cap_rank",
            "fully_diluted_valuation",
            "total_volume",
            "high_24h",
            "low_24h",
            "price_change_24h",
            "price_change_percentage_24h",
            "market_cap_change_24h",
            "market_cap_change_percentage_24h",
            "circulating_supply",
            "total_supply",
            "max_supply",
            "ath",
            "ath_change_percentage",
            "atl",
            "atl_change_percentage",
        }
        for coin in data:
            flattened = flatten_dict(coin)
            row = {}
            for key, value in flattened.items():
                row[key.replace(".", "_")] = value
                column_type = TYPE_FLOAT if key in float_fields else _get_type(value)
                friendly_name = key.replace("_", " ").title()
                if key in ("ath_date", "atl_date"):
                    column_type = TYPE_DATETIME
                if key == "platforms":
                    continue
                add_column(columns, key, column_type, friendly_name)
            rows.append(row)

    elif endpoint_type == "ohlc":
        for ohlc_point in data:
            timestamp, open_price, high_price, low_price, close_price = ohlc_point
            rows.append(
                {
                    "timestamp": timestamp,
                    "datetime": datetime.datetime.fromtimestamp(timestamp / 1000).isoformat(),
                    "open": open_price,
                    "high": high_price,
                    "low": low_price,
                    "close": close_price,
                }
            )
        if rows:
            add_column(columns, "timestamp", TYPE_INTEGER, "Timestamp")
            add_column(columns, "datetime", TYPE_DATETIME, "Date Time")
            add_column(columns, "open", TYPE_FLOAT, "Open")
            add_column(columns, "high", TYPE_FLOAT, "High")
            add_column(columns, "low", TYPE_FLOAT, "Low")
            add_column(columns, "close", TYPE_FLOAT, "Close")

    else:
        # Generic flattening for any other endpoint.
        if isinstance(data, list):
            for item in data:
                flattened = flatten_dict(item)
                row = {}
                for key, value in flattened.items():
                    row[key.replace(".", "_")] = value
                    add_column(columns, key, _get_type(value), key.replace("_", " ").title())
                rows.append(row)
        elif isinstance(data, dict):
            flattened = flatten_dict(data)
            row = {}
            for key, value in flattened.items():
                row[key.replace(".", "_")] = value
                add_column(columns, key, _get_type(value), key.replace("_", " ").title())
            rows.append(row)

    return {"rows": rows, "columns": columns}


class CoinGecko(BaseHTTPQueryRunner):
    """CoinGecko REST query runner. YAML-based query syntax."""

    requires_url = False

    @classmethod
    def name(cls):
        return "CoinGecko"

    @classmethod
    def type(cls):
        return "coingecko"

    @classmethod
    def configuration_schema(cls):
        return {
            "type": "object",
            "properties": {
                "api_key": {
                    "type": "string",
                    "title": "API Key (Optional - for Pro features)",
                    "description": "CoinGecko Pro API key for higher rate limits",
                },
                "base_url": {
                    "type": "string",
                    "title": "Base URL",
                    "default": "https://api.coingecko.com/api/v3",
                    "description": "CoinGecko API base URL",
                },
                "timeout": {
                    "type": "integer",
                    "title": "Request Timeout (seconds)",
                    "default": 30,
                    "description": "HTTP request timeout in seconds",
                },
            },
            "secret": ["api_key"],
            "order": ["base_url", "api_key", "timeout"],
        }

    def __init__(self, configuration):
        super(CoinGecko, self).__init__(configuration)
        self.syntax = "yaml"
        self.base_url = self.configuration.get("base_url") or "https://api.coingecko.com/api/v3"
        self.api_key = self.configuration.get("api_key")
        self.timeout = self.configuration.get("timeout", 30)

    def test_connection(self):
        url = "{0}/ping".format(self.base_url.rstrip("/"))
        response, error = self.get_response(url, headers=self._get_headers(), timeout=self.timeout)
        if error:
            raise Exception(error)
        if response.status_code != 200:
            raise Exception("API returned status code {0}".format(response.status_code))

    def _build_url(self, endpoint):
        url = "{0}/{1}".format(self.base_url.rstrip("/"), endpoint.lstrip("/"))
        # When a Pro API key is configured but the user kept the public base URL,
        # transparently route to pro-api.coingecko.com.
        if self.api_key and url.startswith("https://api.coingecko.com/api/v3"):
            url = url.replace(
                "https://api.coingecko.com/api/v3",
                "https://pro-api.coingecko.com/api/v3",
            )
        return url

    def _get_headers(self):
        headers = {
            "Accept": "application/json",
            "User-Agent": "Rewatch-CoinGecko-QueryRunner/1.0",
        }
        if self.api_key:
            headers["x-cg-pro-api-key"] = self.api_key
        return headers

    def _fetch_new_listings_with_market_data(self, params, chain_filter=None):
        headers = self._get_headers()
        new_listings_url = self._build_url("coins/list/new")

        response, error = self.get_response(new_listings_url, params=params, headers=headers, timeout=self.timeout)
        if error:
            return None, "API request failed: {0}".format(error)
        if response.status_code != 200:
            return None, "API returned status code {0}".format(response.status_code)

        try:
            new_listings = response.json()
        except ValueError as e:
            return None, "Failed to parse JSON response: {0}".format(e)

        coin_ids = [coin.get("id") for coin in new_listings if coin.get("id")]
        if not coin_ids:
            return None, "No valid coin IDs in /coins/list/new response"

        # Bulk fetch /coins/markets in batches of 50 (URL-length safe).
        markets_url = self._build_url("coins/markets")
        all_market_data = []
        for i in range(0, len(coin_ids), 50):
            batch_ids = coin_ids[i : i + 50]
            market_params = {
                "vs_currency": "usd",
                "ids": ",".join(batch_ids),
                "order": "market_cap_desc",
                "per_page": str(len(batch_ids)),
                "page": "1",
                "sparkline": "false",
                "price_change_percentage": "1h,24h,7d",
            }
            market_response, market_error = self.get_response(
                markets_url, params=market_params, headers=headers, timeout=self.timeout
            )
            if market_error or market_response.status_code != 200:
                continue
            try:
                all_market_data.extend(market_response.json())
            except ValueError:
                continue
            time.sleep(0.2)

        if not all_market_data:
            return None, "Failed to fetch market data for newly listed coins"

        # Optional chain filter
        if chain_filter:
            chain_filter_lower = chain_filter.lower().replace("-", "_").replace(" ", "_")
            all_market_data = [
                c
                for c in all_market_data
                if any(chain_filter_lower in (p or "").lower().replace("-", "_") for p in (c.get("platforms") or {}).keys())
            ]

        # Re-attach activated_at
        activation_map = {coin.get("id"): coin.get("activated_at") for coin in new_listings if coin.get("id")}
        for market_coin in all_market_data:
            cid = market_coin.get("id")
            if cid in activation_map and activation_map[cid]:
                market_coin["activated_at"] = activation_map[cid]
                market_coin["activated_datetime"] = datetime.datetime.fromtimestamp(
                    activation_map[cid]
                ).isoformat()

        return json_dumps(parse_coingecko_response(all_market_data, "coins_markets")), None

    def run_query(self, query, user):
        try:
            query_config = parse_query(query)
            if not isinstance(query_config, dict):
                raise QueryParseError("Query should be a YAML object describing the CoinGecko API request.")

            coin_id = query_config.get("coingeckoID", query_config.get("coinId", "bitcoin"))
            endpoint = query_config.get("endpoint", "simple-price")

            endpoint_mapping = {
                "simple-price": ("simple/price", "simple_price"),
                "price": ("simple/price", "simple_price"),
                "market-chart": ("coins/{0}/market_chart".format(coin_id), "market_chart"),
                "market-chart-range": ("coins/{0}/market_chart/range".format(coin_id), "market_chart"),
                "historical": ("coins/{0}/market_chart".format(coin_id), "market_chart"),
                "coin-detail": ("coins/{0}".format(coin_id), "coin_detail"),
                "detail": ("coins/{0}".format(coin_id), "coin_detail"),
                "ohlc": ("coins/{0}/ohlc".format(coin_id), "ohlc"),
                "coins-list": ("coins/list", "coins_list"),
                "list": ("coins/list", "coins_list"),
                "coins-list-platforms": ("coins/list", "coins_list_platforms"),
                "list-platforms": ("coins/list", "coins_list_platforms"),
                "coins-markets": ("coins/markets", "coins_markets"),
                "markets": ("coins/markets", "coins_markets"),
                "new-listings": ("coins/list/new", "new_listings"),
                "newly-listed": ("coins/list/new", "new_listings"),
                "trending": ("search/trending", "generic"),
                "global": ("global", "generic"),
                "exchanges": ("exchanges", "generic"),
                "exchange-rates": ("exchange_rates", "generic"),
                "categories": ("coins/categories", "generic"),
            }

            if endpoint in endpoint_mapping:
                api_path, endpoint_type = endpoint_mapping[endpoint]
            else:
                api_path = endpoint.replace("-", "/")
                endpoint_type = "generic"

            params = dict(query_config.get("params") or {})

            # Fill in sensible defaults per endpoint.
            if endpoint_type == "simple_price":
                params.setdefault("ids", coin_id)
                params.setdefault("vs_currencies", "usd")
            elif endpoint_type == "market_chart":
                params.setdefault("vs_currency", "usd")
                params.setdefault("days", "30")
                # `interval` is only honoured for Pro API users.
                if "interval" in params and not self.api_key:
                    del params["interval"]
            elif endpoint_type == "coins_list":
                params.setdefault("include_platform", "false")
            elif endpoint_type == "coins_list_platforms":
                params["include_platform"] = "true"
            elif endpoint_type == "coins_markets":
                params.setdefault("vs_currency", "usd")
                params.setdefault("order", "market_cap_desc")
                params.setdefault("per_page", "100")
            elif endpoint_type == "ohlc":
                params.setdefault("vs_currency", "usd")
                params.setdefault("days", "30")
                params["interval"] = "daily"
            elif endpoint_type == "new_listings":
                # `/coins/list/new` doesn't accept market params; strip them.
                for k in (
                    "vs_currency",
                    "order",
                    "per_page",
                    "page",
                    "sparkline",
                    "price_change_percentage",
                ):
                    params.pop(k, None)
                chain_filter = params.pop("chain", None)
                return self._fetch_new_listings_with_market_data(params, chain_filter)

            url = self._build_url(api_path)
            response, error = self.get_response(url, params=params, headers=self._get_headers(), timeout=self.timeout)
            if error:
                return None, "API request failed: {0}".format(error)
            if response.status_code != 200:
                return None, "API returned status code {0}".format(response.status_code)

            try:
                data = response.json()
            except ValueError as e:
                return None, "Failed to parse JSON response: {0}".format(e)

            parsed_data = parse_coingecko_response(data, endpoint_type)
            return json_dumps(parsed_data), None

        except QueryParseError as e:
            return None, str(e)
        except Exception as e:
            logger.exception("Error running CoinGecko query")
            return None, "Query execution failed: {0}".format(e)


register(CoinGecko)
