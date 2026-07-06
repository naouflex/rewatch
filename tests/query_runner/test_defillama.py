"""Unit tests for the DefiLlama query runner."""
from unittest import TestCase
from unittest import mock

from rewatch.query_runner.coingecko import QueryParseError
from rewatch.query_runner.defillama import (
    DefiLlama,
    ENDPOINT_BY_SLUG,
    _resolve_path,
    _sample_query,
    _schema_for_endpoint,
    parse_defillama_response,
)


class TestDefiLlamaHelpers(TestCase):
    def test_resolve_path_fills_params(self):
        path = _resolve_path("protocol/{protocol}", {"protocol": "aave"})
        self.assertEqual(path, "protocol/aave")

    def test_resolve_path_missing_param(self):
        self.assertRaises(QueryParseError, _resolve_path, "protocol/{protocol}", {})

    def test_sample_query_includes_endpoint_and_params(self):
        entry = ENDPOINT_BY_SLUG["protocol"]
        sample = _sample_query(entry)
        self.assertIn("endpoint: protocol", sample)
        self.assertIn("protocol: aave", sample)

    def test_schema_for_endpoint_has_category_prefix(self):
        entry = ENDPOINT_BY_SLUG["protocols"]
        schema_item = _schema_for_endpoint(entry)
        self.assertEqual(schema_item["name"], "tvl.protocols")
        self.assertIn("endpoint: protocols", schema_item["insertValue"])


class TestParseDefiLlamaResponse(TestCase):
    def test_timeseries_list(self):
        data = [
            {"date": 1506470400, "tvl": 0},
            {"date": 1506556800, "tvl": 100},
        ]
        result = parse_defillama_response(data)
        self.assertEqual(len(result["rows"]), 2)
        self.assertEqual(result["rows"][0]["tvl"], 0)
        self.assertIn("datetime", result["rows"][0])
        self.assertIn("date", [c["name"] for c in result["columns"]])

    def test_protocol_detail_extracts_tvl_series(self):
        data = {
            "name": "Inverse Finance",
            "tvl": [
                {"date": 1607731200, "totalLiquidityUSD": 40126},
                {"date": 1607817600, "totalLiquidityUSD": 80125},
            ],
        }
        result = parse_defillama_response(data)
        self.assertEqual(len(result["rows"]), 2)
        self.assertEqual(result["rows"][0]["tvl"], 40126)
        self.assertNotIn("name", result["rows"][0])

    def test_coins_prices(self):
        data = {
            "coins": {
                "coingecko:ethereum": {
                    "price": 1754.97,
                    "symbol": "ETH",
                    "timestamp": 1783331411,
                    "confidence": 0.99,
                }
            }
        }
        result = parse_defillama_response(data)
        self.assertEqual(len(result["rows"]), 1)
        self.assertEqual(result["rows"][0]["coin"], "coingecko:ethereum")
        self.assertEqual(result["rows"][0]["price"], 1754.97)

    def test_stablecoin_chart_expands_nested_values(self):
        data = [
            {
                "date": "1511913600",
                "totalCirculating": {"peggedUSD": 109970},
                "totalCirculatingUSD": {"peggedUSD": 110105},
            }
        ]
        result = parse_defillama_response(data)
        self.assertEqual(result["rows"][0]["totalCirculating_peggedUSD"], 109970)
        self.assertEqual(result["rows"][0]["totalCirculatingUSD_peggedUSD"], 110105)

    def test_unwraps_data_wrapper(self):
        data = {"data": [{"name": "Aave", "tvl": 1000000}]}
        result = parse_defillama_response(data)
        self.assertEqual(len(result["rows"]), 1)
        self.assertEqual(result["rows"][0]["name"], "Aave")


class TestDefiLlamaRunner(TestCase):
    def setUp(self):
        self.runner = DefiLlama({})

    def test_metadata(self):
        self.assertEqual(DefiLlama.type(), "defillama")
        self.assertEqual(DefiLlama.name(), "DefiLlama")
        self.assertFalse(DefiLlama.requires_url)

    def test_get_schema_free_includes_free_endpoints(self):
        schema = self.runner.get_schema()
        names = [item["name"] for item in schema]
        self.assertIn("tvl.protocols", names)
        self.assertNotIn("analytics.hacks", names)

    def test_get_schema_pro_includes_pro_endpoints(self):
        runner = DefiLlama({"api_key": "test-key"})
        schema = runner.get_schema()
        names = [item["name"] for item in schema]
        self.assertIn("analytics.hacks", names)

    def test_run_query_protocols(self):
        response = mock.Mock(status_code=200)
        response.json.return_value = [{"name": "Aave", "tvl": 1000000}]

        with mock.patch.object(self.runner, "get_response", return_value=(response, None)):
            data, error = self.runner.run_query("endpoint: protocols", None)

        self.assertIsNone(error)
        self.assertEqual(len(data["rows"]), 1)
        self.assertIn("name", [c["name"] for c in data["columns"]])

    def test_run_query_protocol_timeseries(self):
        response = mock.Mock(status_code=200)
        response.json.return_value = {
            "name": "Aave",
            "tvl": [{"date": 1607731200, "totalLiquidityUSD": 40126}],
        }

        with mock.patch.object(self.runner, "get_response", return_value=(response, None)):
            data, error = self.runner.run_query("endpoint: protocol\nprotocol: aave\n", None)

        self.assertIsNone(error)
        self.assertEqual(len(data["rows"]), 1)
        self.assertEqual(data["rows"][0]["tvl"], 40126)

    def test_run_query_unknown_endpoint(self):
        data, error = self.runner.run_query("endpoint: does-not-exist", None)
        self.assertIsNone(data)
        self.assertIn("Unknown endpoint", error)

    def test_run_query_pro_only_without_key(self):
        data, error = self.runner.run_query("endpoint: hacks", None)
        self.assertIsNone(data)
        self.assertIn("Pro API key", error)

    def test_test_connection(self):
        response = mock.Mock(status_code=200)
        with mock.patch.object(self.runner, "get_response", return_value=(response, None)):
            self.runner.test_connection()
