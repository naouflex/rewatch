from unittest.mock import patch

from httpx import Request, Response
from openai import RateLimitError

from rewatch.assistant.openai_retry import (
    _tpm_shortfall_wait_seconds,
    retry_status_message,
    retry_wait_seconds,
)


def _rate_limit_error(message: str, *, retry_after: str | None = None) -> RateLimitError:
    headers = {"retry-after": retry_after} if retry_after is not None else {}
    request = Request("POST", "https://api.openai.com/v1/chat/completions")
    response = Response(429, headers=headers, request=request, json={"error": {"message": message}})
    return RateLimitError("rate limit", response=response, body=response.json())


class TestOpenAIRetryHelpers:
    def test_retry_wait_prefers_tpm_shortfall_over_short_message_hint(self):
        message = (
            "Rate limit reached for gpt-5.4-mini on tokens per min (TPM): "
            "Limit 200000, Used 176547, Requested 23984. Please try again in 159ms."
        )
        exc = _rate_limit_error(message, retry_after="3")
        wait = retry_wait_seconds(exc, attempt=0)
        assert 8.0 <= wait <= 9.5

    def test_retry_wait_uses_retry_after_header_for_non_tpm_errors(self):
        exc = _rate_limit_error("Too many requests", retry_after="4")
        assert retry_wait_seconds(exc, attempt=0) == 4.0

    def test_retry_wait_parses_message_delay(self):
        exc = _rate_limit_error("Please try again in 2.5 seconds.")
        assert retry_wait_seconds(exc, attempt=0) == 2.5

    def test_tpm_shortfall_wait_seconds(self):
        message = "Limit 200000, Used 176547, Requested 23984"
        wait = _tpm_shortfall_wait_seconds(message)
        assert wait is not None
        assert 8.0 <= wait <= 9.5

    def test_retry_status_message_for_rate_limit(self):
        exc = _rate_limit_error("Rate limit reached")
        message = retry_status_message(exc, 7.4)
        assert "rate limit" in message.lower()
        assert "7s" in message

    @patch("rewatch.assistant.openai_retry.time.sleep")
    def test_call_with_retry_retries_rate_limits(self, sleep_mock):
        from rewatch.assistant.openai_retry import call_with_retry

        attempts = {"count": 0}

        def operation():
            attempts["count"] += 1
            if attempts["count"] < 2:
                raise _rate_limit_error(
                    "Limit 200000, Used 190000, Requested 20000. Please try again in 100ms."
                )
            return "ok"

        statuses: list[str] = []

        result = call_with_retry(
            operation,
            on_status=lambda event: statuses.append(event["message"]),
            log_label="test",
        )

        assert result == "ok"
        assert attempts["count"] == 2
        assert sleep_mock.called
        assert any("rate limit" in message.lower() for message in statuses)
