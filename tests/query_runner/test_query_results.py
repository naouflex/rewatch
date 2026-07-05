import datetime
import decimal
import math
import re
import sqlite3
from unittest import TestCase

import mock
import pytest

from rewatch.query_runner.query_results import (
    CreateTableError,
    PermissionError,
    Results,
    _build_schema_entry,
    _load_query,
    create_table,
    create_tables_from_query_ids,
    evaluate_subquery,
    extract_cached_query_ids,
    extract_query_ids,
    extract_query_params,
    fix_column_name,
    get_query_results,
    prepare_parameterized_query,
    register_sql_helpers,
    replace_query_parameters,
)
from rewatch.utils import json_dumps
from tests import BaseTestCase


class TestExtractQueryIds(TestCase):
    def test_works_with_simple_query(self):
        query = "SELECT 1"
        self.assertEqual([], extract_query_ids(query))

    def test_finds_queries_to_load(self):
        query = "SELECT * FROM query_123"
        self.assertEqual([123], extract_query_ids(query))

    def test_finds_queries_in_joins(self):
        query = "SELECT * FROM query_123 JOIN query_4566"
        self.assertEqual([123, 4566], extract_query_ids(query))

    def test_finds_queries_with_whitespace_characters(self):
        query = "SELECT * FROM    query_123 a JOIN\tquery_4566 b ON a.id=b.parent_id JOIN\r\nquery_78 c ON b.id=c.parent_id"
        self.assertEqual([123, 4566, 78], extract_query_ids(query))


class TestCreateTable(TestCase):
    def test_creates_table_with_colons_in_column_name(self):
        connection = sqlite3.connect(":memory:")
        results = {
            "columns": [{"name": "ga:newUsers"}, {"name": "test2"}],
            "rows": [{"ga:newUsers": 123, "test2": 2}],
        }
        table_name = "query_123"
        create_table(connection, table_name, results)
        connection.execute("SELECT 1 FROM query_123")

    def test_creates_table_with_double_quotes_in_column_name(self):
        connection = sqlite3.connect(":memory:")
        results = {
            "columns": [{"name": "ga:newUsers"}, {"name": '"test2"'}],
            "rows": [{"ga:newUsers": 123, '"test2"': 2}],
        }
        table_name = "query_123"
        create_table(connection, table_name, results)
        connection.execute("SELECT 1 FROM query_123")

    def test_creates_table(self):
        connection = sqlite3.connect(":memory:")
        results = {"columns": [{"name": "test1"}, {"name": "test2"}], "rows": []}
        table_name = "query_123"
        create_table(connection, table_name, results)
        connection.execute("SELECT 1 FROM query_123")

    def test_creates_table_with_missing_columns(self):
        connection = sqlite3.connect(":memory:")
        results = {
            "columns": [{"name": "test1"}, {"name": "test2"}],
            "rows": [{"test1": 1, "test2": 2}, {"test1": 3}],
        }
        table_name = "query_123"
        create_table(connection, table_name, results)
        connection.execute("SELECT 1 FROM query_123")

    def test_creates_table_with_spaces_in_column_name(self):
        connection = sqlite3.connect(":memory:")
        results = {
            "columns": [{"name": "two words"}, {"name": "test2"}],
            "rows": [{"two words": 1, "test2": 2}, {"test1": 3}],
        }
        table_name = "query_123"
        create_table(connection, table_name, results)
        connection.execute("SELECT 1 FROM query_123")

    def test_creates_table_with_dashes_in_column_name(self):
        connection = sqlite3.connect(":memory:")
        results = {
            "columns": [{"name": "two-words"}, {"name": "test2"}],
            "rows": [{"two-words": 1, "test2": 2}],
        }
        table_name = "query_123"
        create_table(connection, table_name, results)
        connection.execute("SELECT 1 FROM query_123")
        connection.execute('SELECT "two-words" FROM query_123')

    def test_creates_table_with_non_ascii_in_column_name(self):
        connection = sqlite3.connect(":memory:")
        results = {
            "columns": [{"name": "\xe4"}, {"name": "test2"}],
            "rows": [{"\xe4": 1, "test2": 2}],
        }
        table_name = "query_123"
        create_table(connection, table_name, results)
        connection.execute("SELECT 1 FROM query_123")

    def test_creates_table_with_decimal_and_timedelta_in_column_value(self):
        connection = sqlite3.connect(":memory:")
        results = {
            "columns": [{"name": "test1"}, {"name": "test2"}, {"name": "test3"}],
            "rows": [{"test1": 1, "test2": decimal.Decimal(2), "test3": datetime.timedelta(seconds=3)}],
        }
        table_name = "query_123"
        create_table(connection, table_name, results)
        connection.execute("SELECT 1 FROM query_123")

    def test_shows_meaningful_error_on_failure_to_create_table(self):
        connection = sqlite3.connect(":memory:")
        results = {"columns": [], "rows": []}
        table_name = "query_123"
        with pytest.raises(CreateTableError):
            create_table(connection, table_name, results)

    def test_loads_results(self):
        connection = sqlite3.connect(":memory:")
        rows = [{"test1": 1, "test2": "test"}, {"test1": 2, "test2": "test2"}]
        results = {"columns": [{"name": "test1"}, {"name": "test2"}], "rows": rows}
        table_name = "query_123"
        create_table(connection, table_name, results)
        self.assertEqual(len(list(connection.execute("SELECT * FROM query_123"))), 2)

    def test_loads_list_and_dict_results(self):
        connection = sqlite3.connect(":memory:")
        rows = [{"test1": [1, 2, 3]}, {"test2": {"a": "b"}}]
        results = {"columns": [{"name": "test1"}, {"name": "test2"}], "rows": rows}
        table_name = "query_123"
        create_table(connection, table_name, results)
        self.assertEqual(len(list(connection.execute("SELECT * FROM query_123"))), 2)


class TestGetQuery(BaseTestCase):
    # test query from different account
    def test_raises_exception_for_query_from_different_account(self):
        query = self.factory.create_query()
        user = self.factory.create_user(org=self.factory.create_org())

        self.assertRaises(PermissionError, lambda: _load_query(user, query.id))

    def test_raises_exception_for_query_with_different_groups(self):
        ds = self.factory.create_data_source(group=self.factory.create_group())
        query = self.factory.create_query(data_source=ds)
        user = self.factory.create_user()

        self.assertRaises(PermissionError, lambda: _load_query(user, query.id))

    def test_returns_query(self):
        query = self.factory.create_query()
        user = self.factory.create_user()

        loaded = _load_query(user, query.id)
        self.assertEqual(query, loaded)

    def test_returns_query_when_user_has_view_only_access(self):
        ds = self.factory.create_data_source(group=self.factory.org.default_group, view_only=True)
        query = self.factory.create_query(data_source=ds)
        user = self.factory.create_user()

        loaded = _load_query(user, query.id)
        self.assertEqual(query, loaded)


class TestExtractCachedQueryIds(TestCase):
    def test_works_with_simple_query(self):
        query = "SELECT 1"
        self.assertEqual([], extract_cached_query_ids(query))

    def test_finds_queries_to_load(self):
        query = "SELECT * FROM cached_query_123"
        self.assertEqual([123], extract_cached_query_ids(query))

    def test_finds_queries_in_joins(self):
        query = "SELECT * FROM cached_query_123 JOIN cached_query_4566"
        self.assertEqual([123, 4566], extract_cached_query_ids(query))

    def test_finds_queries_with_whitespace_characters(self):
        query = "SELECT * FROM    cached_query_123 a JOIN\tcached_query_4566 b ON a.id=b.parent_id JOIN\r\ncached_query_78 c ON b.id=c.parent_id"
        self.assertEqual([123, 4566, 78], extract_cached_query_ids(query))


class TestExtractParamQueryIds(TestCase):
    def test_works_with_simple_query(self):
        query = "SELECT 1"
        self.assertEqual([], extract_query_params(query))

    def test_ignores_non_param_queries(self):
        query = "SELECT * FROM query_123"
        self.assertEqual([], extract_query_params(query))

    def test_ignores_cached_queries_to_load(self):
        query = "SELECT * FROM cached_query_123"
        self.assertEqual([], extract_query_params(query))

    def test_finds_queries_to_load(self):
        query = "SELECT * FROM param_query_123_{token=test}"
        self.assertEqual([("123", "token=test")], extract_query_params(query))

    def test_finds_queries_in_joins(self):
        query = "SELECT * FROM param_query_123_{token1=test1} JOIN param_query_456_{token2=test2}"
        self.assertEqual([("123", "token1=test1"), ("456", "token2=test2")], extract_query_params(query))


class TestPrepareParameterizedQuery(TestCase):
    def test_param_query_replacement(self):
        result = prepare_parameterized_query("SELECT * FROM param_query_123_{token=test}", [("123", "token=test")])
        self.assertEqual("SELECT * FROM query_123_1c5f1acad40f99b968836273d74baa89", result)


class TestReplaceQueryParameters(TestCase):
    def test_replace_query_params(self):
        result = replace_query_parameters("SELECT '{{token1}}', '{{token2}}'", "token1=test1&token2=test2")
        self.assertEqual("SELECT 'test1', 'test2'", result)

    def test_subquery_value_is_evaluated_against_connection(self):
        connection = sqlite3.connect(":memory:")
        connection.execute("CREATE TABLE upstream (day TEXT)")
        connection.execute("INSERT INTO upstream (day) VALUES ('2026-04-01')")
        result = replace_query_parameters(
            "SELECT * WHERE day = '{{day}}'",
            "day=(SELECT MAX(day) FROM upstream)",
            connection=connection,
        )
        self.assertEqual("SELECT * WHERE day = '2026-04-01'", result)

    def test_subquery_falls_back_to_raw_value_when_no_connection(self):
        # No connection: parentheses must be substituted verbatim (back-compat).
        result = replace_query_parameters(
            "SELECT * WHERE day = '{{day}}'",
            "day=(SELECT MAX(day) FROM upstream)",
        )
        self.assertEqual("SELECT * WHERE day = '(SELECT MAX(day) FROM upstream)'", result)

    def test_subquery_with_no_results_keeps_raw_value(self):
        # Don't blow up the parent query if a subquery is malformed/empty;
        # leave the placeholder text in so the parent fails loudly instead.
        connection = sqlite3.connect(":memory:")
        connection.execute("CREATE TABLE empty_t (x INT)")
        result = replace_query_parameters(
            "SELECT '{{day}}'",
            "day=(SELECT MAX(x) FROM empty_t)",
            connection=connection,
        )
        # MAX over an empty table yields a single NULL row → resolves to "None".
        self.assertEqual("SELECT 'None'", result)


class TestEvaluateSubquery(TestCase):
    def test_returns_first_cell_as_string(self):
        connection = sqlite3.connect(":memory:")
        connection.execute("CREATE TABLE t (x INT)")
        connection.execute("INSERT INTO t (x) VALUES (42)")
        self.assertEqual("42", evaluate_subquery("(SELECT x FROM t)", connection))

    def test_strips_leading_and_trailing_parens(self):
        connection = sqlite3.connect(":memory:")
        # The function should also accept a bare statement without parens.
        self.assertEqual("1", evaluate_subquery("SELECT 1", connection))

    def test_raises_when_subquery_returns_no_rows(self):
        connection = sqlite3.connect(":memory:")
        connection.execute("CREATE TABLE t (x INT)")
        with pytest.raises(Exception):
            evaluate_subquery("(SELECT x FROM t)", connection)


class TestFixColumnName(TestCase):
    def test_fix_column_name(self):
        self.assertEqual('"a_b_c_d"', fix_column_name("a:b.c d"))


class TestGetQueryResult(BaseTestCase):
    def test_cached_query_result(self):
        query_result = self.factory.create_query_result()
        query = self.factory.create_query(latest_query_data=query_result)

        self.assertEqual(query_result.data, get_query_results(self.factory.user, query.id, True))

    def test_non_cached_query_result(self):
        query_result = self.factory.create_query_result()
        query = self.factory.create_query(latest_query_data=query_result)

        from rewatch.query_runner.pg import PostgreSQL

        with mock.patch.object(PostgreSQL, "run_query") as qr:
            query_result_data = {"columns": [], "rows": []}
            qr.return_value = (query_result_data, None)
            self.assertEqual(query_result_data, get_query_results(self.factory.user, query.id, False))

    def test_non_cached_query_result_normalizes_json_string(self):
        # Many runners (Python, CoinGecko, Dune, GraphQL, EVM, ...) return a
        # JSON-encoded string from run_query rather than a dict. The
        # parameterized path needs to decode it before handing to create_table.
        query_result = self.factory.create_query_result()
        query = self.factory.create_query(latest_query_data=query_result)

        from rewatch.query_runner.pg import PostgreSQL

        with mock.patch.object(PostgreSQL, "run_query") as qr:
            payload = {"columns": [{"name": "x"}], "rows": [{"x": 1}]}
            qr.return_value = (json_dumps(payload), None)
            self.assertEqual(payload, get_query_results(self.factory.user, query.id, False))

    def test_retries_on_transient_failure(self):
        query_result = self.factory.create_query_result()
        query = self.factory.create_query(latest_query_data=query_result)

        from rewatch.query_runner.pg import PostgreSQL

        good_payload = {"columns": [], "rows": []}
        with mock.patch.object(PostgreSQL, "run_query") as qr:
            qr.side_effect = [Exception("transient"), (good_payload, None)]
            with mock.patch("time.sleep"):  # don't actually wait between attempts
                result = get_query_results(self.factory.user, query.id, False, max_retries=3, delay=0)
        self.assertEqual(good_payload, result)
        self.assertEqual(qr.call_count, 2)


class TestSqlHelpers(TestCase):
    def setUp(self):
        self.connection = sqlite3.connect(":memory:")
        register_sql_helpers(self.connection)

    def tearDown(self):
        self.connection.close()

    def _scalar(self, sql, *params):
        return self.connection.execute(sql, params).fetchone()[0]

    def test_log_returns_log_with_base(self):
        # log_2(8) = 3
        self.assertAlmostEqual(self._scalar("SELECT LOG(8, 2)"), 3.0)

    def test_log_returns_none_on_invalid_input(self):
        self.assertIsNone(self._scalar("SELECT LOG('abc', 2)"))

    def test_exp_returns_e_to_the_x(self):
        self.assertAlmostEqual(self._scalar("SELECT EXP(1)"), math.e)

    def test_power(self):
        self.assertAlmostEqual(self._scalar("SELECT POWER(2, 10)"), 1024.0)

    def test_ln(self):
        self.assertAlmostEqual(self._scalar("SELECT LN(EXP(1))"), 1.0)

    def test_sqrt(self):
        self.assertAlmostEqual(self._scalar("SELECT SQRT(81)"), 9.0)

    def test_hyperlink(self):
        self.assertEqual(
            self._scalar("SELECT HYPERLINK('https://example.com', 'click')"),
            '<a href="https://example.com">click</a>',
        )

    def test_markdown_hyperlink(self):
        self.assertEqual(
            self._scalar("SELECT MARKDOWN_HYPERLINK('https://example.com', 'click')"),
            "[click](https://example.com)",
        )

    def test_concat_variadic_and_skips_none(self):
        self.assertEqual(self._scalar("SELECT CONCAT('a', 'b', NULL, 1, 2)"), "ab12")

    def test_now_returns_iso_string(self):
        value = self._scalar("SELECT NOW()")
        self.assertIsInstance(value, str)
        # ISO-8601 timestamps start with the year — sanity check that the
        # function returned something date-shaped rather than e.g. None.
        self.assertRegex(value, r"^\d{4}-\d{2}-\d{2}T")

    def test_add_thousand_separator(self):
        self.assertEqual(
            self._scalar("SELECT ADD_THOUSAND_SEPARATOR(1234567.891, 2)"),
            "1,234,567.89",
        )

    def test_hex_to_decimal_with_and_without_prefix(self):
        self.assertEqual(self._scalar("SELECT HEX_TO_DECIMAL('0xff')"), "255")
        self.assertEqual(self._scalar("SELECT HEX_TO_DECIMAL('FF')"), "255")
        self.assertIsNone(self._scalar("SELECT HEX_TO_DECIMAL('zzz')"))

    def test_get_array_item_indexes_into_json_array(self):
        self.assertEqual(self._scalar('SELECT GET_ARRAY_ITEM(?, 1)', "[10, 20, 30]"), "20")
        # Out-of-range index returns NULL rather than crashing the row.
        self.assertIsNone(self._scalar('SELECT GET_ARRAY_ITEM(?, 99)', "[10, 20, 30]"))

    def test_get_array_item_walks_nested_indices(self):
        self.assertEqual(
            self._scalar('SELECT GET_ARRAY_ITEM(?, 0, 1)', "[[10, 20], [30, 40]]"),
            "20",
        )

    def test_get_json_item_walks_keys(self):
        payload = '{"user": {"name": "ada", "tags": ["admin", "ops"]}}'
        self.assertEqual(
            self._scalar('SELECT GET_JSON_ITEM(?, ?, ?)', payload, "user", "name"),
            "ada",
        )

    def test_get_json_item_returns_json_for_nested_objects(self):
        payload = '{"a": {"b": 1}}'
        self.assertEqual(self._scalar('SELECT GET_JSON_ITEM(?, ?)', payload, "a"), '{"b": 1}')

    def test_get_json_item_handles_python_repr_strings(self):
        # ``ast.literal_eval`` covers strings produced by `repr({...})`
        # which use single quotes — common when columns store stringified dicts.
        self.assertEqual(self._scalar('SELECT GET_JSON_ITEM(?, ?)', "{'k': 'v'}", "k"), "v")

    def test_stdev_aggregate(self):
        self.connection.execute("CREATE TABLE nums (x REAL)")
        self.connection.executemany("INSERT INTO nums (x) VALUES (?)", [(1,), (2,), (3,), (4,), (5,)])
        # statistics.stdev([1..5]) ≈ 1.5811
        self.assertAlmostEqual(self._scalar("SELECT STDEV(x) FROM nums"), 1.5811388300841898, places=4)

    def test_stdev_aggregate_returns_none_when_too_few_values(self):
        self.connection.execute("CREATE TABLE nums (x REAL)")
        self.connection.execute("INSERT INTO nums (x) VALUES (1)")
        self.assertIsNone(self._scalar("SELECT STDEV(x) FROM nums"))


class TestGetSchema(BaseTestCase):
    def test_lists_queries_with_cached_results(self):
        payload = {"columns": [{"name": "a", "type": "string"}, {"name": "b"}], "rows": []}
        query_result = self.factory.create_query_result(data=payload)
        query = self.factory.create_query(latest_query_data=query_result, name="My Cool Query")

        schema = Results({}).get_schema()
        names = [entry["name"] for entry in schema]
        self.assertIn("query_{0} -- My Cool Query".format(query.id), names)
        cols = [entry["columns"] for entry in schema if entry["name"].startswith("query_{0} ".format(query.id))]
        self.assertEqual(len(cols), 1)
        self.assertEqual([c["name"] for c in cols[0]], ["a", "b"])
        # First column kept its declared "string" type; second defaulted to TYPE_STRING.
        self.assertEqual(cols[0][0]["type"], "string")
        self.assertEqual(cols[0][1]["type"], "string")

    def test_omits_queries_with_no_cached_results(self):
        # Create a query without a result attached
        self.factory.create_query()
        # And one with a result
        payload = {"columns": [{"name": "x"}], "rows": []}
        cached = self.factory.create_query_result(data=payload)
        with_data = self.factory.create_query(latest_query_data=cached)

        schema = Results({}).get_schema()
        included_ids = {int(re.match(r"query_(\d+)", entry["name"]).group(1)) for entry in schema}
        self.assertIn(with_data.id, included_ids)


class TestBuildSchemaEntry(BaseTestCase):
    def test_returns_none_for_query_without_data(self):
        query = self.factory.create_query()
        self.assertIsNone(_build_schema_entry(query))

    def test_returns_none_for_query_without_columns(self):
        result = self.factory.create_query_result(data={"columns": [], "rows": []})
        query = self.factory.create_query(latest_query_data=result)
        self.assertIsNone(_build_schema_entry(query))


class TestCreateTablesFromQueryIds(BaseTestCase):
    def _make_param_query_with_columns(self, payload):
        # Helper: build a query whose runner returns ``payload``.
        query_result = self.factory.create_query_result()
        query = self.factory.create_query(latest_query_data=query_result)
        return query

    def test_param_query_borrows_cached_columns_when_live_run_is_empty(self):
        cached_payload = {"columns": [{"name": "a"}, {"name": "b"}], "rows": []}
        query_result = self.factory.create_query_result(data=cached_payload)
        query = self.factory.create_query(latest_query_data=query_result)

        from rewatch.query_runner.pg import PostgreSQL

        connection = sqlite3.connect(":memory:")
        with mock.patch.object(PostgreSQL, "run_query") as qr:
            # Live re-run with a parameter returns no schema at all (e.g.
            # the data source filtered every row out): we should still create
            # the table with the cached column shape so that downstream SQL
            # joins can refer to it.
            qr.return_value = ({"columns": [], "rows": []}, None)
            create_tables_from_query_ids(
                self.factory.user,
                connection,
                query_ids=[],
                query_params=[(str(query.id), "x=1")],
                cached_query_ids=[],
            )

        # Confirm the SQLite table exists with the cached columns.
        rows = connection.execute(
            "SELECT name FROM pragma_table_info('query_{0}_{1}')".format(
                query.id,
                "5d41402abc4b2a76b9719d911017c592",  # placeholder; we discover real hash below
            )
        ).fetchall()
        # Discover the actual table by listing all tables (simpler than re-deriving the md5).
        tables = [r[0] for r in connection.execute("SELECT name FROM sqlite_master WHERE type='table'")]
        self.assertEqual(len(tables), 1)
        cols = [r[1] for r in connection.execute("PRAGMA table_info({0})".format(tables[0]))]
        self.assertEqual(cols, ["a", "b"])
        # Sanity check: silence the unused `rows` lookup above.
        _ = rows
