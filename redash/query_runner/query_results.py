import ast
import datetime
import decimal
import hashlib
import logging
import math
import re
import sqlite3
import statistics
import time
from urllib.parse import parse_qs

from rewatch import models
from rewatch.permissions import has_access, view_only
from rewatch.query_runner import (
    TYPE_STRING,
    BaseQueryRunner,
    JobTimeoutException,
    guess_type,
    register,
)
from rewatch.utils import json_dumps, json_loads

logger = logging.getLogger(__name__)


class PermissionError(Exception):
    pass


class CreateTableError(Exception):
    pass


def extract_query_params(query):
    return re.findall(r"(?:join|from)\s+param_query_(\d+)_{([^}]+)}", query, re.IGNORECASE)


def extract_query_ids(query):
    queries = re.findall(r"(?:join|from)\s+query_(\d+)", query, re.IGNORECASE)
    return [int(q) for q in queries]


def extract_cached_query_ids(query):
    queries = re.findall(r"(?:join|from)\s+cached_query_(\d+)", query, re.IGNORECASE)
    return [int(q) for q in queries]


def _load_query(user, query_id):
    query = models.Query.get_by_id(query_id)

    if user.org_id != query.org_id:
        raise PermissionError("Query id {} not found.".format(query.id))

    # TODO: this duplicates some of the logic we already have in the rewatch.handlers.query_results.
    # We should merge it so it's consistent.
    if not has_access(query.data_source, user, view_only):
        raise PermissionError("You do not have access to query id {}.".format(query.id))

    return query


def evaluate_subquery(subquery, connection):
    """Run an inline ``(SELECT ...)`` against the in-memory SQLite connection
    and return the first cell as a string. Used to resolve parameter values
    that themselves depend on other queries that have already been loaded
    into the connection (e.g. ``param_query_3_{day=(SELECT MAX(day) FROM
    cached_query_5)}``)."""
    cursor = connection.cursor()
    stripped = subquery.strip()
    if stripped.startswith("(") and stripped.endswith(")"):
        stripped = stripped[1:-1]
    cursor.execute(stripped)
    row = cursor.fetchone()
    if not row:
        raise ValueError("Parameter subquery returned no rows: {0}".format(subquery))
    return str(row[0])


def replace_query_parameters(query_text, params, connection=None):
    """Substitute ``{{name}}`` placeholders in ``query_text`` from a
    URL-encoded ``params`` string. When a value is wrapped in parentheses and
    a SQLite ``connection`` is supplied, the value is evaluated as a subquery
    against that connection before substitution."""
    qs = parse_qs(params)
    for key, value in qs.items():
        raw = value[0]
        if connection is not None and raw.strip().startswith("(") and raw.strip().endswith(")"):
            try:
                resolved = evaluate_subquery(raw, connection)
            except Exception as e:
                logger.warning("Subquery parameter '%s' failed to evaluate: %s", key, e)
                resolved = raw
            query_text = query_text.replace("{{{{{my_key}}}}}".format(my_key=key), resolved)
        else:
            query_text = query_text.replace("{{{{{my_key}}}}}".format(my_key=key), raw)
    return query_text


def _normalize_runner_result(results):
    """Some query runners (Python, CoinGecko, Dune, GraphQL, the EVM ones,
    ...) return a JSON-encoded string from ``run_query`` while SQL runners
    return a dict. ``create_table`` always wants a dict, so coerce it."""
    if isinstance(results, (bytes, bytearray)):
        results = results.decode("utf-8")
    if isinstance(results, str):
        return json_loads(results)
    return results


def get_query_results(user, query_id, bring_from_cache, params=None, connection=None, max_retries=1, delay=0.2):
    """Load the rows + columns for ``query_id``.

    ``params`` activates the parameterized path (``run_query`` is invoked).
    When a SQLite ``connection`` is provided and a parameter value is wrapped
    in ``(...)``, that subquery is evaluated against ``connection`` before
    substitution. ``max_retries`` retries transient runner errors with
    exponential-ish ``delay`` between attempts (defaults to a single attempt
    to preserve the historical behaviour)."""
    last_error = None
    for attempt in range(max(1, max_retries)):
        try:
            query = _load_query(user, query_id)
            if bring_from_cache:
                if query.latest_query_data_id is not None:
                    return query.latest_query_data.data
                raise Exception("No cached result available for query {}.".format(query.id))

            query_text = query.query_text
            if params is not None:
                query_text = replace_query_parameters(query_text, params, connection=connection)

            results, error = query.data_source.query_runner.run_query(query_text, user)
            if error:
                raise Exception("Failed loading results for query id {}: {}".format(query.id, error))
            return _normalize_runner_result(results)
        except Exception as e:
            last_error = e
            if attempt < max_retries - 1:
                time.sleep(delay)
                continue
            raise
    # Shouldn't be reached, but keep mypy / readers happy.
    raise last_error if last_error else RuntimeError("get_query_results: unknown error")


def _cached_columns_or_none(user, query_id):
    """Best-effort fallback used when a non-cached child query returns no
    rows; we still want a ``CREATE TABLE`` with the right column names."""
    try:
        cached = get_query_results(user, query_id, True)
        return cached.get("columns") or None
    except Exception:
        return None


def create_tables_from_query_ids(user, connection, query_ids, query_params, cached_query_ids=[]):
    for query_id in set(cached_query_ids):
        results = get_query_results(user, query_id, True)
        table_name = "cached_query_{query_id}".format(query_id=query_id)
        create_table(connection, table_name, results)

    for query in set(query_params):
        results = get_query_results(user, query[0], False, query[1], connection=connection)
        # If a parameterized child returned an empty schema (some runners do
        # when a where-clause filters everything out), borrow the cached
        # column shape so the SQLite table can still be created.
        if isinstance(results, dict) and not results.get("columns"):
            cached_cols = _cached_columns_or_none(user, int(query[0]))
            if cached_cols:
                results["columns"] = cached_cols
        table_hash = hashlib.md5(
            "query_{query}_{hash}".format(query=query[0], hash=query[1]).encode(), usedforsecurity=False
        ).hexdigest()
        table_name = "query_{query_id}_{param_hash}".format(query_id=query[0], param_hash=table_hash)
        create_table(connection, table_name, results)

    for query_id in set(query_ids):
        results = get_query_results(user, query_id, False)
        if isinstance(results, dict) and not results.get("columns"):
            cached_cols = _cached_columns_or_none(user, query_id)
            if cached_cols:
                results["columns"] = cached_cols
        table_name = "query_{query_id}".format(query_id=query_id)
        create_table(connection, table_name, results)


def fix_column_name(name):
    return '"{}"'.format(re.sub(r'[:."\s]', "_", name, flags=re.UNICODE))


def flatten(value):
    if isinstance(value, (list, dict)):
        return json_dumps(value)
    elif isinstance(value, decimal.Decimal):
        return float(value)
    elif isinstance(value, datetime.timedelta):
        return str(value)
    else:
        return value


def create_table(connection, table_name, query_results):
    try:
        columns = [column["name"] for column in query_results["columns"]]
        safe_columns = [fix_column_name(column) for column in columns]

        column_list = ", ".join(safe_columns)
        create_table = "CREATE TABLE {table_name} ({column_list})".format(
            table_name=table_name, column_list=column_list
        )
        logger.debug("CREATE TABLE query: %s", create_table)
        connection.execute(create_table)
    except sqlite3.OperationalError as exc:
        raise CreateTableError("Error creating table {}: {}".format(table_name, str(exc)))

    insert_template = "insert into {table_name} ({column_list}) values ({place_holders})".format(
        table_name=table_name,
        column_list=column_list,
        place_holders=",".join(["?"] * len(columns)),
    )

    for row in query_results["rows"]:
        values = [flatten(row.get(column)) for column in columns]
        connection.execute(insert_template, values)


def prepare_parameterized_query(query, query_params):
    for params in query_params:
        table_hash = hashlib.md5(
            "query_{query}_{hash}".format(query=params[0], hash=params[1]).encode(), usedforsecurity=False
        ).hexdigest()
        key = "param_query_{query_id}_{{{param_string}}}".format(query_id=params[0], param_string=params[1])
        value = "query_{query_id}_{param_hash}".format(query_id=params[0], param_hash=table_hash)
        query = query.replace(key, value)
    return query


# ---------------------------------------------------------------------------
# Custom SQL helpers (registered on the in-memory SQLite connection)
# ---------------------------------------------------------------------------
#
# These mirror the ones inverse-watch ships in its Query Results runner.
# Every helper swallows exceptions and returns ``None`` so that a single bad
# row never aborts the whole query — the same UX as upstream BigQuery /
# Postgres ``SAFE_CAST`` style functions.


def _sql_safe(default=None):
    """Wrap a SQL helper so that any exception logs and returns ``default``."""

    def deco(fn):
        def wrapper(*args):
            try:
                return fn(*args)
            except Exception as e:  # pragma: no cover - logged for the user
                logger.warning("SQL helper %s(%s) failed: %s", fn.__name__, args, e)
                return default

        wrapper.__name__ = fn.__name__
        return wrapper

    return deco


@_sql_safe()
def sql_log(x, base):
    return math.log(float(x), float(base))


@_sql_safe()
def sql_exp(x):
    return math.exp(float(x))


@_sql_safe()
def sql_power(x, y):
    return math.pow(float(x), float(y))


@_sql_safe()
def sql_ln(x):
    return math.log(float(x))


@_sql_safe()
def sql_sqrt(x):
    return math.sqrt(float(x))


@_sql_safe()
def sql_hyperlink(href, label):
    return '<a href="{0}">{1}</a>'.format(href, label)


@_sql_safe()
def sql_markdown_hyperlink(href, label):
    return "[{0}]({1})".format(label, href)


@_sql_safe()
def sql_concat(*args):
    return "".join("" if a is None else str(a) for a in args)


@_sql_safe()
def sql_now():
    # SQLite returns datetime objects via the default adapter, but some users
    # call NOW() in expressions where a string is more useful.
    return datetime.datetime.utcnow().isoformat()


@_sql_safe(default="0.00")
def sql_add_thousand_separator(x, decimal_places):
    return "{:,.{decimal_places}f}".format(float(x), decimal_places=int(decimal_places))


@_sql_safe()
def sql_hex_to_decimal(hex_str):
    if hex_str is None:
        return None
    cleaned = str(hex_str).strip()
    if cleaned.lower().startswith("0x"):
        cleaned = cleaned[2:]
    return str(int(cleaned, 16))


def _safe_parse(value):
    """Parse a JSON-ish string without ever using ``eval``.

    ``ast.literal_eval`` accepts Python-literal forms (single quotes, tuples)
    while still being safe; it covers the cases real users hit when storing
    arrays/objects in CSV columns or string fields without quoting them as
    strict JSON.
    """
    if isinstance(value, (list, dict)):
        return value
    if not isinstance(value, str):
        return None
    stripped = value.strip()
    if not stripped:
        return None
    try:
        return json_loads(stripped)
    except Exception:
        try:
            return ast.literal_eval(stripped)
        except Exception:
            return None


@_sql_safe()
def sql_get_array_item(value, *path):
    """``GET_ARRAY_ITEM(arr, idx [, idx2 ...])`` indexes into a JSON array."""
    parsed = _safe_parse(value)
    if not isinstance(parsed, list):
        return None
    cursor = parsed
    for key in path:
        try:
            cursor = cursor[int(key)]
        except (TypeError, ValueError, IndexError, KeyError):
            return None
    if isinstance(cursor, (list, dict)):
        return json_dumps(cursor)
    return str(cursor)


@_sql_safe()
def sql_get_json_item(value, *path):
    """``GET_JSON_ITEM(obj, key [, key2 ...])`` walks into a JSON object."""
    parsed = _safe_parse(value)
    if parsed is None:
        return None
    cursor = parsed
    for key in path:
        try:
            cursor = cursor[key]
        except (TypeError, KeyError, IndexError):
            try:
                cursor = cursor[int(key)]
            except (TypeError, ValueError, KeyError, IndexError):
                return None
    if isinstance(cursor, (list, dict)):
        return json_dumps(cursor)
    return str(cursor)


class _StdevAggregate:
    """SQL aggregate equivalent of ``statistics.stdev``."""

    def __init__(self):
        self._values = []

    def step(self, value):
        if value is None:
            return
        try:
            self._values.append(float(value))
        except (TypeError, ValueError):
            pass

    def finalize(self):
        if len(self._values) < 2:
            return None
        try:
            return statistics.stdev(self._values)
        except statistics.StatisticsError:
            return None


def register_sql_helpers(connection):
    """Attach the inverse-watch helper functions to a SQLite connection."""
    connection.create_function("LOG", 2, sql_log)
    connection.create_function("EXP", 1, sql_exp)
    connection.create_function("POWER", 2, sql_power)
    connection.create_function("LN", 1, sql_ln)
    connection.create_function("SQRT", 1, sql_sqrt)
    connection.create_function("HYPERLINK", 2, sql_hyperlink)
    connection.create_function("MARKDOWN_HYPERLINK", 2, sql_markdown_hyperlink)
    connection.create_function("CONCAT", -1, sql_concat)
    connection.create_function("NOW", 0, sql_now)
    connection.create_function("ADD_THOUSAND_SEPARATOR", 2, sql_add_thousand_separator)
    connection.create_function("HEX_TO_DECIMAL", 1, sql_hex_to_decimal)
    connection.create_function("GET_ARRAY_ITEM", -1, sql_get_array_item)
    connection.create_function("GET_JSON_ITEM", -1, sql_get_json_item)
    connection.create_aggregate("STDEV", 1, _StdevAggregate)


# Default cap on how many query rows we surface in ``get_schema``. Schema
# fetches are background-task driven and we want the autocomplete dropdown
# to stay responsive, so we cut off at a sane number. Users can still
# reference any query by id even if it isn't in the dropdown.
SCHEMA_QUERY_LIMIT = 500


def _build_schema_entry(query):
    """Return a ``{"name": ..., "columns": [...]}`` row for a given Query.

    Returns ``None`` if the query has no usable cached result."""
    if query.latest_query_data is None:
        return None
    data = query.latest_query_data.data
    if not isinstance(data, dict):
        return None
    cols = data.get("columns") or []
    columns = []
    for column in cols:
        if not isinstance(column, dict):
            continue
        name = column.get("name")
        if not name:
            continue
        columns.append({"name": name, "type": column.get("type") or TYPE_STRING})
    if not columns:
        return None
    table_name = "query_{0}".format(query.id)
    friendly = (query.name or "").strip()
    if friendly:
        table_name = "{0} -- {1}".format(table_name, friendly)
    return {"name": table_name, "columns": columns}


class Results(BaseQueryRunner):
    should_annotate_query = False
    noop_query = "SELECT 1"

    @classmethod
    def configuration_schema(cls):
        return {"type": "object", "properties": {}}

    @classmethod
    def name(cls):
        return "Query Results"

    def get_schema(self, get_stats=False):
        """Surface the most recent queries (with cached results) so that the
        SQL editor's autocomplete shows them as ``query_<id>`` tables.

        The Query Results runner is org-agnostic in the data model — there's
        no link from a runner instance back to its data source / org — so we
        list newest queries across the install up to ``SCHEMA_QUERY_LIMIT``.
        Permissions are still enforced at execution time inside
        ``_load_query``: the schema is informational only.
        """
        try:
            queries = (
                models.Query.query.filter(models.Query.latest_query_data_id.isnot(None))
                .order_by(models.Query.id.desc())
                .limit(SCHEMA_QUERY_LIMIT)
                .all()
            )
        except Exception:
            logger.exception("query_results.get_schema: failed to fetch queries")
            return []

        schema = []
        for query in queries:
            try:
                entry = _build_schema_entry(query)
            except Exception as e:
                logger.debug("get_schema: skipping query %s: %s", query.id, e)
                continue
            if entry is not None:
                schema.append(entry)
        return schema

    def run_query(self, query, user):
        connection = sqlite3.connect(":memory:")
        register_sql_helpers(connection)

        query_ids = extract_query_ids(query)

        query_params = extract_query_params(query)

        cached_query_ids = extract_cached_query_ids(query)
        create_tables_from_query_ids(user, connection, query_ids, query_params, cached_query_ids)

        cursor = connection.cursor()

        if query_params is not None:
            query = prepare_parameterized_query(query, query_params)

        try:
            cursor.execute(query)

            if cursor.description is not None:
                columns = self.fetch_columns([(i[0], None) for i in cursor.description])

                rows = []
                column_names = [c["name"] for c in columns]

                for i, row in enumerate(cursor):
                    for j, col in enumerate(row):
                        guess = guess_type(col)

                        if columns[j]["type"] is None:
                            columns[j]["type"] = guess
                        elif columns[j]["type"] != guess:
                            columns[j]["type"] = TYPE_STRING

                    rows.append(dict(zip(column_names, row)))

                data = {"columns": columns, "rows": rows}
                error = None
            else:
                error = "Query completed but it returned no data."
                data = None
        except (KeyboardInterrupt, JobTimeoutException):
            connection.cancel()
            raise
        finally:
            connection.close()
        return data, error


register(Results)
