"""Unit tests for the DefiLlama query runner."""
import json
from unittest import TestCase
from unittest import mock

from rewatch.query_runner.coingecko import QueryParseError
from rewatch.query_runner.defillama import (
    DefiLlama,
    ENDPOINT_BY_SLUG,
    _resolve_path,
    _sample_query,
    _schema_for_endpoint,
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
        parsed = json.loads(data)
        self.assertEqual(len(parsed["rows"]), 1)
        self.assertIn("name", [c["name"] for c in parsed["columns"]])

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
