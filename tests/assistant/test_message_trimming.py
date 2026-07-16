"""Tests for chat history trimming before it is sent to the LLM."""

from unittest import TestCase, mock

from rewatch.assistant import storage


def _fit(messages, *, max_messages=10, max_chars=100):
    with mock.patch.object(storage, "assistant_max_llm_messages", return_value=max_messages), mock.patch.object(
        storage, "assistant_max_llm_chars", return_value=max_chars
    ):
        return storage.fit_messages_for_llm(messages)


class TestFitMessagesForLlm(TestCase):
    def test_within_limits_is_untouched(self):
        messages = [
            {"role": "user", "content": "hi"},
            {"role": "assistant", "content": "hello"},
        ]
        self.assertEqual(_fit(messages), messages)

    def test_drops_oldest_messages_first(self):
        messages = [
            {"role": "user", "content": "a" * 60},
            {"role": "assistant", "content": "b" * 60},
            {"role": "user", "content": "c" * 60},
        ]
        trimmed = _fit(messages, max_chars=130)
        self.assertEqual(trimmed, messages[1:])

    def test_message_count_limit_applies(self):
        messages = [{"role": "user", "content": str(i)} for i in range(20)]
        trimmed = _fit(messages, max_messages=5, max_chars=10_000)
        self.assertEqual(len(trimmed), 5)
        self.assertEqual(trimmed[-1]["content"], "19")

    def test_never_drops_the_newest_message(self):
        # A single oversized newest message used to empty the whole list.
        messages = [
            {"role": "user", "content": "old"},
            {"role": "user", "content": "x" * 500},
        ]
        trimmed = _fit(messages, max_chars=100)
        self.assertEqual(len(trimmed), 1)
        self.assertEqual(trimmed[0]["content"], "x" * 100)
        self.assertEqual(trimmed[0]["role"], "user")

    def test_truncation_does_not_mutate_original(self):
        newest = {"role": "user", "content": "x" * 500}
        _fit([newest], max_chars=100)
        self.assertEqual(len(newest["content"]), 500)

    def test_empty_history(self):
        self.assertEqual(_fit([]), [])
