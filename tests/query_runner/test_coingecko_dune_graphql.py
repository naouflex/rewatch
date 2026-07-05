"""Unit tests for the CoinGecko, Dune and GraphQL query runners.

These tests exercise the parsing / column-inference paths without making
real HTTP calls; ``BaseHTTPQueryRunner.get_response`` is mocked so each test
only validates the runner's own logic.
"""
import json
from unittest import TestCase
from unittest import mock

from rewatch.query_runner.coingecko import (
    CoinGecko,
    QueryParseError,
    flatten_dict,
    parse_coingecko_response,
    parse_query as parse_coingecko_query,
)
from rewatch.query_runner.dune import Dune
from rewatch.query_runner.graphql import (
    GraphQL,
    flatten_dict as graphql_flatten,
    parse_response as parse_graphql_response,
)


class TestCoinGeckoParser(TestCase):
    def test_parse_query_rejects_empty(self):
        self.assertRaises(QueryParseError, parse_coingecko_query, "  ")

    def test_simple_price_response(self):
        data = {"bitcoin": {"usd": 60000.5}, "ethereum": {"usd": 3000.0}}
        out = parse_coingecko_response(data, "simple_price")
        self.assertEqual(len(out["rows"]), 2)
        names = [c["name"] for c in out["columns"]]
        self.assertIn("coin_id", names)
        self.assertIn("price_usd", names)

    def test_market_chart_response(self):
        data = {
            "prices": [[1700000000000, 100.0], [1700003600000, 105.0]],
            "market_caps": [[1700000000000, 1.0], [1700003600000, 2.0]],
        }
        out = parse_coingecko_response(data, "market_chart")
        self.assertEqual(len(out["rows"]), 2)
        first = out["rows"][0]
        self.assertEqual(first["timestamp"], 1700000000000)
        self.assertIn("datetime", first)
        self.assertEqual(first["price"], 100.0)
        self.assertEqual(first["market_cap"], 1.0)

    def test_flatten_dict_handles_nested(self):
        out = flatten_dict({"a": {"b": 1, "c": {"d": 2}}})
        self.assertEqual(out, {"a.b": 1, "a.c.d": 2})


class TestCoinGeckoRunner(TestCase):
    def setUp(self):
        self.runner = CoinGecko({"api_key": "", "base_url": "https://api.coingecko.com/api/v3"})

    def test_metadata(self):
        self.assertEqual(CoinGecko.type(), "coingecko")
        self.assertEqual(CoinGecko.name(), "CoinGecko")
        self.assertFalse(CoinGecko.requires_url)

    def test_build_url_uses_pro_when_key_present(self):
        runner = CoinGecko({"api_key": "key", "base_url": "https://api.coingecko.com/api/v3"})
        url = runner._build_url("ping")
        self.assertTrue(url.startswith("https://pro-api.coingecko.com/api/v3/"))

    def test_build_url_keeps_custom_base(self):
        runner = CoinGecko({"base_url": "https://custom.example/api"})
        self.assertEqual(runner._build_url("ping"), "https://custom.example/api/ping")

    def test_get_schema_includes_endpoints_and_categories(self):
        schema = self.runner.get_schema()
        names = [item["name"] for item in schema]
        self.assertIn("market.simple-price", names)
        self.assertIn("reference.coins-list", names)
        self.assertIn("detail.coin-detail", names)

    def test_get_schema_includes_top_coins(self):
        response = mock.Mock(status_code=200)
        response.json.return_value = [
            {"id": "bitcoin", "name": "Bitcoin", "symbol": "btc", "market_cap_rank": 1},
            {"id": "ethereum", "name": "Ethereum", "symbol": "eth", "market_cap_rank": 2},
        ]
        with mock.patch.object(self.runner, "get_response", return_value=(response, None)):
            schema = self.runner.get_schema()
        coin_names = [item["name"] for item in schema if item["name"].startswith("coins.")]
        self.assertIn("coins.bitcoin", coin_names)
        self.assertIn("coins.ethereum", coin_names)
        bitcoin = next(item for item in schema if item["name"] == "coins.bitcoin")
        self.assertEqual(bitcoin["displayName"], "Bitcoin (BTC)")
        self.assertIn("coingeckoID: bitcoin", bitcoin["insertValue"])

    def test_run_query_simple_price(self):
        response = mock.Mock(status_code=200)
        response.json.return_value = {"bitcoin": {"usd": 60000}}

        with mock.patch.object(self.runner, "get_response", return_value=(response, None)):
            data, error = self.runner.run_query("endpoint: simple-price\ncoingeckoID: bitcoin", None)

        self.assertIsNone(error)
        self.assertEqual(data["rows"][0]["coin_id"], "bitcoin")
        self.assertEqual(data["rows"][0]["price_usd"], 60000)

    def test_run_query_returns_error_on_non_dict_yaml(self):
        data, error = self.runner.run_query("just a string", None)
        self.assertIsNone(data)
        self.assertIn("YAML object", error)


class TestDuneRunner(TestCase):
    def setUp(self):
        self.runner = Dune({"api_key": "secret"})

    def test_metadata(self):
        self.assertEqual(Dune.type(), "dune")
        self.assertEqual(Dune.name(), "Dune")
        self.assertFalse(Dune.requires_url)

    def test_run_query_missing_query_id(self):
        data, error = self.runner.run_query("performance: medium", None)
        self.assertIsNone(data)
        self.assertIn("query_id", error)

    def test_run_query_polls_until_completed(self):
        execute_response = mock.Mock(status_code=200)
        execute_response.json.return_value = {"execution_id": "exec-1"}
        running_status = mock.Mock(status_code=200)
        running_status.json.return_value = {"state": "QUERY_STATE_PENDING"}
        completed_status = mock.Mock(status_code=200)
        completed_status.json.return_value = {"state": "QUERY_STATE_COMPLETED"}
        results_response = mock.Mock(status_code=200)
        results_response.json.return_value = {
            "result": {
                "metadata": {"column_names": ["chain", "txs"]},
                "rows": [{"chain": "ethereum", "txs": 1}],
            }
        }

        sequence = iter(
            [
                (execute_response, None),
                (running_status, None),
                (completed_status, None),
                (results_response, None),
            ]
        )

        with mock.patch("time.sleep"):  # don't actually wait between polls
            with mock.patch.object(
                self.runner, "get_response", side_effect=lambda *a, **kw: next(sequence)
            ):
                data, error = self.runner.run_query("query_id: 42", None)

        self.assertIsNone(error)
        payload = json.loads(data)
        self.assertEqual([c["name"] for c in payload["columns"]], ["chain", "txs"])
        self.assertEqual(payload["rows"][0]["chain"], "ethereum")

    def test_run_query_failed_state_returns_error(self):
        execute_response = mock.Mock(status_code=200)
        execute_response.json.return_value = {"execution_id": "exec-1"}
        failed_status = mock.Mock(status_code=200)
        failed_status.json.return_value = {"state": "QUERY_STATE_FAILED", "error": "boom"}

        sequence = iter([(execute_response, None), (failed_status, None)])
        with mock.patch.object(
            self.runner, "get_response", side_effect=lambda *a, **kw: next(sequence)
        ):
            data, error = self.runner.run_query("query_id: 42", None)
        self.assertIsNone(data)
        self.assertIn("QUERY_STATE_FAILED", error)


class TestGraphQLParser(TestCase):
    def test_flatten_lists_and_dicts(self):
        data = {"a": {"b": 1}, "c": [{"d": 2}, {"d": 3}]}
        out = graphql_flatten(data)
        self.assertEqual(out["a_b"], 1)
        # The flatten reuses the parent key for list items
        self.assertEqual(out["c_d"], 3)

    def test_parse_response_unwraps_root_list(self):
        data = {"transfers": [{"id": "1", "amount": 100}, {"id": "2", "amount": 200}]}
        out = parse_graphql_response(data)
        self.assertEqual(len(out["rows"]), 2)
        names = [c["name"] for c in out["columns"]]
        self.assertIn("id", names)
        self.assertIn("amount", names)

    def test_parse_response_with_block_number(self):
        out = parse_graphql_response({"x": [{"id": 1}]}, block_number=123)
        self.assertEqual(out["rows"][0]["block_number"], 123)


class TestGraphQLRunner(TestCase):
    def setUp(self):
        self.runner = GraphQL({"url": "https://example.test/graphql"})

    def test_metadata(self):
        self.assertEqual(GraphQL.type(), "graphql")
        self.assertEqual(self.runner.syntax, "graphql")

    def test_run_query_empty(self):
        data, error = self.runner.run_query("", None)
        self.assertIsNone(data)
        self.assertIn("empty", error.lower())

    def test_run_query_paginates_until_short_page(self):
        first_page = mock.Mock(status_code=200)
        first_page.json.return_value = {
            "data": {"items": [{"id": str(i), "v": i} for i in range(1000)]}
        }
        last_page = mock.Mock(status_code=200)
        last_page.json.return_value = {"data": {"items": [{"id": "1001", "v": 1001}]}}
        sequence = iter([(first_page, None), (last_page, None)])

        with mock.patch.object(
            self.runner, "get_response", side_effect=lambda *a, **kw: next(sequence)
        ):
            data, error = self.runner.run_query(
                'query { items(first: $first, where: {id_gt: "$id_gt"}) { id v } }', None
            )

        self.assertIsNone(error)
        payload = json.loads(data)
        self.assertEqual(len(payload["rows"]), 1001)
