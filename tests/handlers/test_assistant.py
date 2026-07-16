from unittest import TestCase
from unittest.mock import patch

from flask import Flask
from werkzeug.exceptions import HTTPException

from rewatch import settings
from rewatch.handlers.assistant import _assistant_base_url
from tests import BaseTestCase


class TestAssistantBaseUrl(TestCase):
    def setUp(self):
        self.app = Flask(__name__)

    def test_configured_host_wins(self):
        with self.app.test_request_context(base_url="http://evil.example.com/"):
            with patch.object(settings, "HOST", "https://rewatch.example.com/"):
                self.assertEqual(_assistant_base_url(), "https://rewatch.example.com")

    def test_localhost_fallback_allowed_without_host(self):
        with self.app.test_request_context(base_url="http://localhost:5001/"):
            with patch.object(settings, "HOST", ""):
                self.assertEqual(_assistant_base_url(), "http://localhost:5001")

    def test_non_local_host_header_rejected_without_host(self):
        # The user's API key is sent to this URL for every tool call, so a
        # client-controlled Host header must never define it.
        with self.app.test_request_context(base_url="http://attacker.example.com/"):
            with patch.object(settings, "HOST", ""):
                with self.assertRaises(HTTPException) as ctx:
                    _assistant_base_url()
                self.assertEqual(ctx.exception.code, 503)


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

    @patch("rewatch.handlers.assistant.generate_query")
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


class TestAssistantChatStreamResource(BaseTestCase):
    @patch("rewatch.handlers.assistant.assistant_enabled", return_value=True)
    @patch("rewatch.handlers.assistant.chat")
    def test_stream_emits_error_event_when_chat_fails(self, chat_mock, _enabled_mock):
        chat_mock.side_effect = RuntimeError("llm exploded")

        rv = self.make_request(
            "post",
            "/api/assistant/chat/stream",
            data={"message": "hello"},
        )

        self.assertEqual(rv.status_code, 200)
        body = rv.data.decode("utf-8")
        self.assertIn('"type": "thread_started"', body)
        self.assertIn('"type": "error"', body)
        self.assertIn("llm exploded", body)
        self.assertNotIn('"type": "complete"', body)

    @patch("rewatch.handlers.assistant.assistant_enabled", return_value=True)
    @patch("rewatch.handlers.assistant.chat")
    def test_stream_emits_complete_event_on_success(self, chat_mock, _enabled_mock):
        chat_mock.return_value = {
            "reply": "All done.",
            "messages": [
                {"role": "user", "content": "hello"},
                {"role": "assistant", "content": "All done."},
            ],
            "decision_graph": None,
        }

        rv = self.make_request(
            "post",
            "/api/assistant/chat/stream",
            data={"message": "hello"},
        )

        self.assertEqual(rv.status_code, 200)
        body = rv.data.decode("utf-8")
        self.assertIn('"type": "complete"', body)
        self.assertIn("All done.", body)
