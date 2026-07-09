"""Shared Anthropic retry helpers for assistant API calls."""

from __future__ import annotations

import logging
import time
from typing import Any, Callable, Optional, TypeVar

from anthropic import (
    APIConnectionError,
    APITimeoutError,
    InternalServerError,
    RateLimitError,
)

from rewatch import settings

logger = logging.getLogger(__name__)

RETRYABLE_ERRORS = (RateLimitError, APIConnectionError, APITimeoutError, InternalServerError)
MAX_API_ATTEMPTS = 5

ActivityCallback = Callable[[dict[str, Any]], None]
T = TypeVar("T")


def create_anthropic_client():
    if not settings.ANTHROPIC_API_KEY:
        raise RuntimeError("Anthropic API key is not configured")
    from anthropic import Anthropic

    return Anthropic(api_key=settings.ANTHROPIC_API_KEY, max_retries=0)


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


def retry_wait_seconds(exc: Exception, attempt: int) -> float:
    if isinstance(exc, RateLimitError):
        wait = _header_retry_after_seconds(exc)
        if wait is not None and wait > 0:
            return min(max(wait, 0.25), 90.0)
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
    log_label: str = "Anthropic",
) -> T:
    """Run an Anthropic call with shared transient-error retries."""
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
