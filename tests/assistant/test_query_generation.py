"""Tests for LLM query generation context and schema formatting."""
from unittest import TestCase

from rewatch.assistant.catalog import build_query_generation_context
from rewatch.assistant.query_generation import _format_schema, _runner_context, _system_prompt


class TestQueryGenerationContext(TestCase):
    def test_coingecko_context_includes_yaml_rules_and_endpoints(self):
        ctx = build_query_generation_context("coingecko")
        self.assertEqual(ctx["syntax"], "yaml")
        self.assertIn("endpoint", ctx["query_keys"])
        self.assertNotIn("url", ctx["query_keys"])
        self.assertTrue(len(ctx["example_queries"]) >= 2)
        self.assertTrue(len(ctx["endpoint_catalog"]) > 0)
        self.assertTrue(any("endpoint:" in ex for ex in ctx["example_queries"]))
        coin_detail = next(item for item in ctx["endpoint_catalog"] if item["endpoint"] == "coin-detail")
        self.assertIn("endpoint: coin-detail", coin_detail["example_query"])
        self.assertIn("coingeckoID:", coin_detail["example_query"])

    def test_get_query_runner_type_coingecko_query_syntax(self):
        from rewatch.assistant.catalog import get_query_runner_type

        docs = get_query_runner_type("coingecko")
        self.assertIn("query_syntax", docs)
        self.assertIn("endpoint:", docs["query_syntax"])
        self.assertIn("url", docs["query_syntax"])
        self.assertIn("JSON data source", docs["query_syntax"])

    def test_defillama_context_includes_endpoints(self):
        ctx = build_query_generation_context("defillama")
        self.assertEqual(ctx["syntax"], "yaml")
        self.assertTrue(any(entry["endpoint"] == "protocols" for entry in ctx["endpoint_catalog"]))

    def test_runner_context_text_for_coingecko(self):
        text = _runner_context("coingecko", "yaml")
        self.assertIn("Query syntax: YAML", text)
        self.assertIn("endpoint:", text)
        self.assertIn("Available endpoints:", text)

    def test_system_prompt_yaml_not_sql(self):
        prompt = _system_prompt("yaml")
        self.assertIn("YAML", prompt)
        self.assertIn("never output SQL", prompt)


class TestSchemaFormatting(TestCase):
    def test_format_schema_includes_yaml_templates(self):
        schema = [
            {
                "name": "market.simple-price",
                "displayName": "simple-price",
                "description": "Current price for a coin",
                "insertValue": "endpoint: simple-price\ncoingeckoID: ethereum\n",
                "columns": [{"name": "coingeckoID", "type": "string"}],
            }
        ]
        text = _format_schema(schema, "yaml")
        self.assertIn("market.simple-price", text)
        self.assertIn("Template:", text)
        self.assertIn("endpoint: simple-price", text)

    def test_format_schema_summarizes_dynamic_coins(self):
        schema = [
            {
                "name": "coins.bitcoin",
                "displayName": "Bitcoin (BTC)",
                "insertValue": "endpoint: simple-price\ncoingeckoID: bitcoin\n",
                "columns": [],
            },
            {
                "name": "coins.ethereum",
                "displayName": "Ethereum (ETH)",
                "insertValue": "endpoint: simple-price\ncoingeckoID: ethereum\n",
                "columns": [],
            },
        ]
        text = _format_schema(schema, "yaml")
        self.assertIn("2 popular coins", text)
        self.assertIn("Bitcoin (BTC)", text)

    def test_format_schema_sql_columns(self):
        schema = [{"name": "users", "columns": [{"name": "id", "type": "integer"}]}]
        text = _format_schema(schema, "sql")
        self.assertIn("users", text)
        self.assertIn("id (integer)", text)
