from unittest import TestCase

from rewatch.query_runner.pg import PostgreSQL, _connect_params, _parse_dsn, build_schema


class TestParameters(TestCase):
    def test_parse_dsn(self):
        configuration = {"dsn": "application_name=rewatch connect_timeout=5"}
        self.assertDictEqual(_parse_dsn(configuration), {"application_name": "rewatch", "connect_timeout": "5"})

    def test_parse_dsn_not_permitted(self):
        configuration = {"dsn": "password=xyz"}
        self.assertRaises(ValueError, _parse_dsn, configuration)

    def test_connect_params_from_connection_string(self):
        configuration = {
            "connectionString": "postgresql://alice:secret@db.example.com:5433/analytics",
            "dsn": "application_name=rewatch",
        }
        params, ssl_config, extra_dsn = _connect_params(configuration)
        self.assertEqual(params["user"], "alice")
        self.assertEqual(params["password"], "secret")
        self.assertEqual(params["host"], "db.example.com")
        self.assertEqual(params["port"], "5433")
        self.assertEqual(params["dbname"], "analytics")
        self.assertEqual(params["application_name"], "rewatch")
        self.assertEqual(ssl_config["sslmode"], "prefer")
        self.assertEqual(extra_dsn, {"application_name": "rewatch"})

    def test_connect_params_from_individual_fields(self):
        configuration = {
            "host": "127.0.0.1",
            "port": 5432,
            "user": "postgres",
            "password": "pw",
            "dbname": "rewatch",
            "dsn": "connect_timeout=5",
        }
        params, _, extra_dsn = _connect_params(configuration)
        self.assertEqual(params["host"], "127.0.0.1")
        self.assertEqual(params["port"], 5432)
        self.assertEqual(params["user"], "postgres")
        self.assertEqual(params["password"], "pw")
        self.assertEqual(params["dbname"], "rewatch")
        self.assertEqual(params["connect_timeout"], "5")
        self.assertEqual(extra_dsn, {"connect_timeout": "5"})

    def test_configuration_schema_accepts_connection_string(self):
        schema = PostgreSQL.configuration_schema()
        from rewatch.utils.configuration import ConfigurationContainer

        config = ConfigurationContainer(
            {"connectionString": "postgresql://user:pass@localhost:5432/app"},
            schema,
        )
        self.assertTrue(config.is_valid())

    def test_configuration_schema_still_requires_dbname_without_connection_string(self):
        schema = PostgreSQL.configuration_schema()
        from rewatch.utils.configuration import ConfigurationContainer

        config = ConfigurationContainer({"host": "127.0.0.1"}, schema)
        self.assertFalse(config.is_valid())


class TestBuildSchema(TestCase):
    def test_handles_dups_between_public_and_other_schemas(self):
        results = {
            "rows": [
                {
                    "table_schema": "public",
                    "table_name": "main.users",
                    "column_name": "id",
                },
                {"table_schema": "main", "table_name": "users", "column_name": "id"},
                {"table_schema": "main", "table_name": "users", "column_name": "name"},
            ]
        }

        schema = {}

        build_schema(results, schema)

        self.assertIn("main.users", schema.keys())
        self.assertListEqual(schema["main.users"]["columns"], ["id", "name"])
        self.assertIn('public."main.users"', schema.keys())
        self.assertListEqual(schema['public."main.users"']["columns"], ["id"])

    def test_build_schema_with_data_types(self):
        results = {
            "rows": [
                {"table_schema": "main", "table_name": "users", "column_name": "id", "data_type": "integer"},
                {"table_schema": "main", "table_name": "users", "column_name": "name", "data_type": "varchar"},
            ]
        }

        schema = {}

        build_schema(results, schema)

        self.assertListEqual(
            schema["main.users"]["columns"], [{"name": "id", "type": "integer"}, {"name": "name", "type": "varchar"}]
        )
