"""GraphQL query runner.

Supports two modes:

- Plain GraphQL queries with optional cursor-pagination via ``$first`` /
  ``$id_gt`` placeholders (the same convention used in subgraph queries).
- Block-range pagination: when the query contains
  ``block: {number: "<spec>"}``, ``<spec>`` is parsed and the query is replayed
  for each block in the range. Supported specs: ``start-lag`` and
  ``start-end-lag`` (where ``start`` / ``end`` accept ``latest`` and negative
  offsets like ``-100``). Block helpers require ``web3`` and an ``RPC_URL``
  environment variable; if either is missing the runner still serves
  non-block queries.

Ported from inverse-watch.
"""
import copy
import datetime
import json
import logging
import os
import re

from funcy import compact

from redash.query_runner import (
    TYPE_BOOLEAN,
    TYPE_DATETIME,
    TYPE_FLOAT,
    TYPE_INTEGER,
    TYPE_STRING,
    BaseHTTPQueryRunner,
    register,
)
from redash.utils import json_dumps

try:
    from web3 import Web3

    web3_installed = True
except ImportError:
    Web3 = None
    web3_installed = False


logger = logging.getLogger(__name__)


def _w3():
    if not web3_installed:
        raise RuntimeError("web3 is not installed; block-range queries require web3 + RPC_URL.")
    rpc_url = os.environ.get("RPC_URL")
    if not rpc_url:
        raise RuntimeError("RPC_URL environment variable is required for block-range queries.")
    return Web3(Web3.HTTPProvider(rpc_url))


def get_current_block_number():
    return _w3().eth.block_number


def get_block_timestamp(block_number):
    return _w3().eth.get_block(block_number).timestamp


def get_last_line_id(data):
    """Return the ``id`` of the last item in the first list-valued field of ``data``."""
    try:
        list_key = next(key for key in data if isinstance(data[key], list))
        return data[list_key][-1]["id"]
    except (StopIteration, KeyError, IndexError, TypeError):
        return 0


def _get_type(value):
    if isinstance(value, bool):
        return TYPE_BOOLEAN
    if isinstance(value, int):
        # Postgres INTEGER tops out at 2^31; bigints are safer as TEXT.
        return TYPE_STRING if value > 2**32 else TYPE_INTEGER
    if isinstance(value, float):
        return TYPE_FLOAT
    if isinstance(value, datetime.datetime):
        return TYPE_DATETIME
    return TYPE_STRING


def _get_column_by_name(columns, column_name):
    for c in columns:
        if c.get("name") == column_name:
            return c
    return None


def add_column(columns, column_name, column_type):
    if _get_column_by_name(columns, column_name) is None:
        columns.append({"name": column_name, "friendly_name": column_name, "type": column_type})


def _sort_columns_with_fields(columns, fields):
    if fields:
        columns = compact([_get_column_by_name(columns, field) for field in fields])
    return columns


def flatten_dict(data, parent_key="", sep="_"):
    items = []
    for k, v in data.items():
        new_key = "{0}{1}{2}".format(parent_key, sep, k) if parent_key else k
        if isinstance(v, dict):
            items.extend(flatten_dict(v, new_key, sep=sep).items())
        elif isinstance(v, list):
            for i in v:
                if isinstance(i, dict):
                    items.extend(flatten_dict(i, new_key, sep=sep).items())
                else:
                    items.append((new_key, i))
        else:
            items.append((new_key, v))
    return dict(items)


def _normalize_response(data):
    """Coerce a top-level GraphQL response into a list of records.

    GraphQL responses are wrapped in their root field (e.g. ``{"transfers": [...]}``).
    This helper unwraps the first list-valued root, while a single root with a
    dict value yields a one-row table.
    """
    if isinstance(data, dict):
        try:
            first_key = next(iter(data))
        except StopIteration:
            return []
        if isinstance(data[first_key], list):
            return data[first_key]
        return [data]
    if isinstance(data, list):
        return data
    return []


def parse_response(data, fields=None, block_number=None):
    rows = []
    columns = []
    if block_number is not None:
        add_column(columns, "block_number", TYPE_INTEGER)
        add_column(columns, "block_time", TYPE_INTEGER)

    for row in _normalize_response(data):
        parsed_row = flatten_dict(row)
        if block_number is not None:
            parsed_row["block_number"] = block_number
            try:
                parsed_row["block_time"] = get_block_timestamp(block_number)
            except RuntimeError:
                parsed_row["block_time"] = None

        for key, value in parsed_row.items():
            if "timestamp" in key.lower():
                try:
                    parsed_row[key] = int(value)
                except (TypeError, ValueError):
                    pass
                add_column(columns, key, TYPE_INTEGER)
            else:
                add_column(columns, key, _get_type(value))
        rows.append(parsed_row)

    return {"rows": rows, "columns": _sort_columns_with_fields(columns, fields)}


class GraphQL(BaseHTTPQueryRunner):
    @classmethod
    def configuration_schema(cls):
        return {
            "type": "object",
            "properties": {
                "url": {"type": "string", "title": "GraphQL endpoint URL"},
            },
            "required": ["url"],
            "secret": [],
        }

    @classmethod
    def type(cls):
        return "graphql"

    def __init__(self, configuration):
        super(GraphQL, self).__init__(configuration)
        self.syntax = "graphql"

    # ------------------------------------------------------------------ schema

    def _get_fields(self, type_):
        try:
            kind = type_.get("kind")
            if kind in ("LIST", "NON_NULL"):
                if "ofType" in type_ and type_["ofType"]:
                    return self._get_fields(type_["ofType"])
                return None, ValueError("Missing 'ofType' for kind {0}".format(kind))
            if kind in ("OBJECT", "INTERFACE", "ENUM"):
                introspect_query = (
                    '{ __type(name: "%s") { fields { name, type { name, kind, ofType { name, kind } } } } }'
                    % type_["name"]
                )
                return self.get_response(
                    self.configuration["url"],
                    http_method="post",
                    json={"query": introspect_query},
                )
            return None, None
        except Exception as e:
            logger.warning("_get_fields exception: %s", e)
            return None, e

    def _get_type_name(self, type_):
        if type_ is None:
            return None
        if isinstance(type_, dict):
            kind = type_.get("kind")
            if kind in ("LIST", "NON_NULL"):
                if "ofType" in type_ and type_["ofType"]:
                    return self._get_type_name(type_["ofType"])
                return kind
            if kind in ("OBJECT", "INTERFACE", "ENUM", "INPUT_OBJECT"):
                return kind
            return type_.get("name")
        return None

    def get_schema(self, get_stats=False):
        try:
            schema = {}
            introspection_query = """
            query IntrospectionQuery {
                __schema {
                    queryType { name, fields { name, type { name, kind, ofType { name, kind } } } }
                    mutationType { name, fields { name, type { name, kind, ofType { name, kind } } } }
                }
            }
            """
            response, error = self.get_response(
                self.configuration["url"],
                http_method="post",
                json={"query": introspection_query},
            )
            if error or response.status_code != 200:
                logger.info("Failed to fetch GraphQL schema.")
                return []

            schema_dict = response.json()
            for type_ in schema_dict["data"]["__schema"]["queryType"]["fields"]:
                table_name = type_["name"]
                schema[table_name] = {"name": table_name, "columns": []}
                fields_response, fields_error = self._get_fields(type_["type"])
                if fields_error or fields_response is None:
                    continue
                if fields_response.status_code != 200:
                    continue
                for field in fields_response.json()["data"]["__type"]["fields"]:
                    schema[table_name]["columns"].append(
                        {
                            "name": field["name"],
                            "type": self._get_type_name(field["type"]) or "unknown",
                        }
                    )
            return list(schema.values())
        except Exception as e:
            logger.warning("get_schema exception: %s", e)
            return []

    # ---------------------------------------------------------- block helpers

    def _resolve_block_number(self, block_str, current_block):
        if block_str.lower() == "latest":
            return current_block
        block_num = int(block_str)
        if block_num < 0:
            return current_block + block_num
        return block_num

    def _parse_block_spec(self, spec, current_block):
        # Allow leading minus on the first part for negative offsets.
        if spec.startswith("-"):
            parts = ["-" + spec[1:].split("-")[0]] + spec[1:].split("-")[1:]
        else:
            parts = spec.split("-")

        if len(parts) == 2:
            return self._resolve_block_number(parts[0], current_block), None, int(parts[1])
        if len(parts) == 3:
            start = self._resolve_block_number(parts[0], current_block)
            end = current_block if parts[1].lower() == "latest" else self._resolve_block_number(parts[1], current_block)
            return start, end, int(parts[2])
        raise ValueError(
            "Invalid block spec '{0}'. Expected 'start-lag' or 'start-end-lag'.".format(spec)
        )

    # ------------------------------------------------------------- run_query

    def _post(self, query_text):
        return self.get_response(
            self.configuration["url"],
            http_method="post",
            headers={"Content-Type": "application/json"},
            json={"query": query_text},
        )

    def _paginate(self, query_text, block_number=None):
        """Run ``$first`` / ``$id_gt`` cursor pagination until exhausted."""
        rows = []
        columns = None
        id_gt = 0
        limit = 1000
        while True:
            paginated = query_text.replace("$first", str(limit)).replace("$id_gt", str(id_gt))
            response, error = self._post(paginated)
            if error:
                return None, error
            if response.status_code != 200:
                return None, "Failed to execute query. Status code: {0}".format(response.status_code)

            payload = response.json()
            if "errors" in payload:
                return None, "Errors in query execution: {0}".format(payload["errors"])

            data = payload.get("data") or {}
            formatted = parse_response(data, fields=None, block_number=block_number)
            rows.extend(formatted["rows"])
            columns = formatted["columns"]

            if len(formatted["rows"]) < limit:
                break
            id_gt = get_last_line_id(data)
        return {"rows": rows, "columns": columns or []}, None

    def run_query(self, query, user):
        if not query.strip():
            return None, "Query is empty."

        block_match = re.search(r'block:\s*\{number:\s*["\']([^"\']+)["\']', query)
        if block_match:
            try:
                current_block = get_current_block_number()
            except RuntimeError as e:
                return None, str(e)
            try:
                start, end, lag = self._parse_block_spec(block_match.group(1), current_block)
            except ValueError as e:
                return None, str(e)
            if end is None:
                end = current_block

            all_rows = []
            columns = None
            block = start
            while block <= end:
                block_query = re.sub(
                    r'block:\s*\{number:\s*["\'][^"\']+["\']\s*\}',
                    'block: {{number: {0}}}'.format(block),
                    query,
                )
                page, error = self._paginate(block_query, block_number=block)
                if error:
                    return None, error
                all_rows.extend(page["rows"])
                columns = page["columns"]
                block += lag

            return json_dumps({"rows": all_rows, "columns": columns or []}), None

        result, error = self._paginate(query)
        if error:
            return None, error
        return json_dumps(result), None


register(GraphQL)
