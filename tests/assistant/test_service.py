"""Tests for the assistant chat loop (LLM and tool execution mocked)."""

import json
from unittest import TestCase, mock

from rewatch.assistant import service


def _chat(**overrides):
    kwargs = {
        "messages": [{"role": "user", "content": "hello"}],
        "base_url": "http://localhost:5001",
        "api_key": "test-key",
        "help_base_url": "https://help.example.com",
    }
    kwargs.update(overrides)
    return service.chat(**kwargs)


class TestChatLoop(TestCase):
    def test_direct_reply_without_tools(self):
        with mock.patch.object(
            service, "stream_completion", return_value={"content": "Hi there", "tool_calls": []}
        ):
            result = _chat()
        self.assertEqual(result["reply"], "Hi there")
        self.assertEqual(result["messages"][-1], {"role": "assistant", "content": "Hi there"})

    def test_tool_round_then_reply(self):
        turns = [
            {
                "content": "",
                "tool_calls": [{"id": "t1", "name": "run_query", "arguments": '{"query_id": 5}'}],
            },
            {"content": "Query ran fine.", "tool_calls": []},
        ]
        executed = []

        def fake_execute(ctx, name, args):
            executed.append((name, args))
            return json.dumps({"row_count": 3})

        with mock.patch.object(service, "stream_completion", side_effect=turns), mock.patch.object(
            service, "execute_tool", side_effect=fake_execute
        ):
            result = _chat()

        self.assertEqual(executed, [("run_query", {"query_id": 5})])
        self.assertEqual(result["reply"], "Query ran fine.")

    def test_invalid_tool_arguments_recover_without_executing(self):
        turns = [
            {
                "content": "",
                "tool_calls": [{"id": "t1", "name": "run_query", "arguments": '{"query_id": '}],
            },
            {"content": "Recovered.", "tool_calls": []},
        ]
        with mock.patch.object(service, "stream_completion", side_effect=turns), mock.patch.object(
            service, "execute_tool"
        ) as execute_mock:
            result = _chat()

        execute_mock.assert_not_called()
        self.assertEqual(result["reply"], "Recovered.")

    def test_tool_budget_exhaustion_forces_summary(self):
        calls = []

        def fake_stream(conversation, on_activity, *, tool_choice="auto"):
            calls.append(tool_choice)
            if tool_choice == "none":
                return {"content": "Here is a summary of progress.", "tool_calls": []}
            return {
                "content": "",
                "tool_calls": [{"id": f"t{len(calls)}", "name": "run_query", "arguments": "{}"}],
            }

        with mock.patch.object(service, "stream_completion", side_effect=fake_stream), mock.patch.object(
            service, "execute_tool", return_value=json.dumps({"ok": True})
        ), mock.patch.object(service, "assistant_max_tool_rounds", return_value=2):
            result = _chat()

        self.assertEqual(calls, ["auto", "auto", "none"])
        self.assertEqual(result["reply"], "Here is a summary of progress.")

    def test_llm_failure_returns_fallback_reply(self):
        with mock.patch.object(service, "stream_completion", side_effect=RuntimeError("api down")):
            result = _chat()
        self.assertIn("error talking to the AI service", result["reply"])
        self.assertIn("api down", result["reply"])

    def test_tool_error_payload_is_recorded_and_loop_continues(self):
        turns = [
            {
                "content": "",
                "tool_calls": [{"id": "t1", "name": "get_query", "arguments": '{"query_id": 9}'}],
            },
            {"content": "That query does not exist.", "tool_calls": []},
        ]
        with mock.patch.object(service, "stream_completion", side_effect=turns), mock.patch.object(
            service, "execute_tool", return_value=json.dumps({"error": "GET /api/queries/9 failed (404)"})
        ):
            result = _chat()
        self.assertEqual(result["reply"], "That query does not exist.")
        graph = result["decision_graph"]
        self.assertTrue(graph)
