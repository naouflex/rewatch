from unittest.mock import patch

from tests import BaseTestCase


class TestAssistantGenerateQueryResource(BaseTestCase):
    def test_generate_query_requires_prompt(self):
        data_source = self.factory.create_data_source()
        rv = self.make_request(
            "post",
            "/api/assistant/generate-query",
            data={"data_source_id": data_source.id},
        )
        self.assertEqual(rv.status_code, 400)

    def test_generate_query_requires_data_source(self):
        rv = self.make_request(
            "post",
            "/api/assistant/generate-query",
            data={"prompt": "show all users"},
        )
        self.assertEqual(rv.status_code, 400)

    @patch("redash.handlers.assistant.generate_query")
    def test_generate_query_returns_query_text(self, generate_query_mock):
        generate_query_mock.return_value = "SELECT * FROM users"
        data_source = self.factory.create_data_source()

        rv = self.make_request(
            "post",
            "/api/assistant/generate-query",
            data={
                "prompt": "show all users",
                "data_source_id": data_source.id,
                "syntax": "sql",
            },
        )

        self.assertEqual(rv.status_code, 200)
        self.assertEqual(rv.json["query"], "SELECT * FROM users")
        generate_query_mock.assert_called_once()
