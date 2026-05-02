"""Dune Analytics query runner.

Queries are written as YAML, e.g.

    query_id: 1234567
    query_parameters:
      chain: ethereum
    performance: medium

The runner POSTs an execution to the Dune API, polls until completion, and
returns the rows / column metadata as Redash-style ``{rows, columns}``.
Ported from inverse-watch.
"""
import logging
import time

import yaml

from redash.query_runner import BaseHTTPQueryRunner, register
from redash.utils import json_dumps

logger = logging.getLogger(__name__)


class Dune(BaseHTTPQueryRunner):
    requires_url = False

    @classmethod
    def configuration_schema(cls):
        return {
            "type": "object",
            "properties": {
                "api_key": {"type": "string", "title": "API Key"},
            },
            "required": ["api_key"],
            "secret": ["api_key"],
        }

    def __init__(self, configuration):
        super(Dune, self).__init__(configuration)
        self.syntax = "yaml"

    def test_connection(self):
        # Dune doesn't expose a cheap "ping" endpoint that doesn't burn quota.
        # We just confirm an API key was configured; meaningful errors will
        # surface when the user runs an actual query.
        if not self.configuration.get("api_key"):
            raise Exception("api_key is required.")

    def run_query(self, query, user):
        try:
            query_params = yaml.safe_load(query) or {}
        except yaml.YAMLError as e:
            return None, "Invalid YAML format: {0}".format(e)

        if not isinstance(query_params, dict):
            return None, "Query must be a YAML object."

        query_id = query_params.get("query_id")
        if not query_id:
            return None, "Missing required field 'query_id'."

        request_data = {
            "query_parameters": query_params.get("query_parameters", {}),
            "performance": query_params.get("performance", "medium"),
        }

        headers = {
            "X-Dune-API-Key": self.configuration["api_key"],
            "Content-Type": "application/json",
        }

        execute_url = "https://api.dune.com/api/v1/query/{0}/execute".format(query_id)
        response, error = self.get_response(execute_url, headers=headers, json=request_data, http_method="post")
        if error:
            return None, error

        execution_id = response.json().get("execution_id")
        if not execution_id:
            return None, "Dune did not return an execution_id."

        # Poll for completion. Dune executions are typically a few seconds
        # for free queries but can run for minutes for `performance: large`.
        while True:
            status_url = "https://api.dune.com/api/v1/execution/{0}/status".format(execution_id)
            status_response, error = self.get_response(status_url, headers=headers)
            if error:
                return None, error

            status_json = status_response.json()
            state = status_json.get("state")
            if state == "QUERY_STATE_COMPLETED":
                break
            if state in ("QUERY_STATE_FAILED", "QUERY_STATE_CANCELLED"):
                return None, "Dune execution {0}: {1}".format(state, status_json)
            time.sleep(5)

        results_url = "https://api.dune.com/api/v1/execution/{0}/results".format(execution_id)
        results_response, error = self.get_response(results_url, headers=headers)
        if error:
            return None, error

        results_json = results_response.json()
        if "result" not in results_json:
            return None, "Unexpected Dune response: {0}".format(results_json)

        try:
            column_names = results_json["result"]["metadata"]["column_names"]
            rows = results_json["result"]["rows"]
        except (KeyError, TypeError) as e:
            return None, "Could not parse Dune results: {0}".format(e)

        columns = [{"name": col, "friendly_name": col} for col in column_names]
        return json_dumps({"columns": columns, "rows": rows}), None

    def get_schema(self, get_stats=False):
        return []


register(Dune)
