"""Shared OpenAI retry helpers for assistant API calls."""

from __future__ import annotations

import logging
import re
import time
from typing import Any, Callable, Optional, TypeVar

from openai import (
    APIConnectionError,
    APITimeoutError,
    InternalServerError,
    OpenAI,
    RateLimitError,
)

from rewatch import settings

logger = logging.getLogger(__name__)

RETRYABLE_ERRORS = (RateLimitError, APIConnectionError, APITimeoutError, InternalServerError)
MAX_API_ATTEMPTS = 5

_RETRY_AFTER_MESSAGE_RE = re.compile(
    r"try again in\s+(\d+(?:\.\d+)?)\s*(ms|milliseconds?|s|sec(?:onds?)?)\b",
    re.IGNORECASE,
)
_TPM_LIMITS_RE = re.compile(
    r"Limit\s+(\d+)\s*,\s*Used\s+(\d+)\s*,\s*Requested\s+(\d+)",
    re.IGNORECASE,
)

ActivityCallback = Callable[[dict[str, Any]], None]
T = TypeVar("T")


def create_openai_client() -> OpenAI:
    if not settings.OPENAI_API_KEY:
        raise RuntimeError("OpenAI API key is not configured")
    # Handle retries ourselves so users see status updates and we can apply
    # TPM-aware backoff instead of the SDK's short default retries.
    return OpenAI(api_key=settings.OPENAI_API_KEY, max_retries=0)


def _header_retry_after_seconds(exc: RateLimitError) -> Optional[float]:
    response = getattr(exc, "response", None)
    if response is None:
        return None
    raw = response.headers.get("retry-after")
    if raw is None:
        return None
    try:
        return max(0.0, float(raw))
    except (TypeError, ValueError):
        return None


def _message_retry_after_seconds(message: str) -> Optional[float]:
    match = _RETRY_AFTER_MESSAGE_RE.search(message or "")
    if not match:
        return None
    value = float(match.group(1))
    unit = match.group(2).lower()
    if unit.startswith("m"):
        return value / 1000.0
    return value


def _tpm_shortfall_wait_seconds(message: str) -> Optional[float]:
    match = _TPM_LIMITS_RE.search(message or "")
    if not match:
        return None
    limit, used, requested = (int(match.group(i)) for i in range(1, 4))
    if limit <= 0 or requested <= 0:
        return None
    if used + requested <= limit:
        return None
    tokens_per_second = limit / 60.0
    # TPM is a sliding window — wait long enough for this request's token budget
    # to free up, not just until the immediate overage clears.
    return requested / tokens_per_second + 1.0


def retry_wait_seconds(exc: Exception, attempt: int) -> float:
    """Compute how long to wait before retrying a transient OpenAI error."""
    if isinstance(exc, RateLimitError):
        message = str(exc)
        body = getattr(exc, "body", None)
        if isinstance(body, dict):
            err = body.get("error") or {}
            if isinstance(err, dict) and err.get("message"):
                message = str(err["message"])

        waits = [
            _tpm_shortfall_wait_seconds(message),
            _header_retry_after_seconds(exc),
            _message_retry_after_seconds(message),
        ]
        for wait in waits:
            if wait is not None and wait > 0:
                return min(max(wait, 0.25), 90.0)

    # Generic exponential backoff for other transient failures.
    return min(2**attempt, 30.0)


def retry_status_message(exc: Exception, wait_seconds: float) -> str:
    if isinstance(exc, RateLimitError):
        seconds = max(1, int(round(wait_seconds)))
        return f"AI rate limit reached — waiting {seconds}s before retrying…"
    return "AI service hiccup — retrying…"


def call_with_retry(
    operation: Callable[[], T],
    *,
    on_status: Optional[ActivityCallback] = None,
    can_retry: Optional[Callable[[], bool]] = None,
    log_label: str = "OpenAI",
) -> T:
    """Run an OpenAI call with shared transient-error retries."""
    last_error: Optional[Exception] = None
    for attempt in range(MAX_API_ATTEMPTS):
        try:
            return operation()
        except RETRYABLE_ERRORS as exc:
            last_error = exc
            if can_retry is not None and not can_retry():
                raise
            if attempt >= MAX_API_ATTEMPTS - 1:
                break
            wait = retry_wait_seconds(exc, attempt)
            logger.warning("%s transient error (attempt %s): %s", log_label, attempt + 1, exc)
            if on_status:
                on_status({"type": "status", "message": retry_status_message(exc, wait)})
            time.sleep(wait)

    raise last_error  # type: ignore[misc]
