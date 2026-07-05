"""Generate query text from natural language for the query editor."""

from __future__ import annotations

import logging
import re
from typing import Any, Optional

from openai import (
    APIConnectionError,
    APITimeoutError,
    InternalServerError,
    OpenAI,
    RateLimitError,
)

from redash import settings
from redash.assistant.catalog import get_query_runner_type, summarize_runner_for_type

logger = logging.getLogger(__name__)

_RETRYABLE_ERRORS = (RateLimitError, APIConnectionError, APITimeoutError, InternalServerError)
_MAX_API_ATTEMPTS = 3
_MAX_SCHEMA_TABLES = 40
_MAX_SCHEMA_COLUMNS = 30

SYSTEM_PROMPT = """You are a query authoring assistant embedded in Rewatch (a data platform).

The user describes what they want in plain language. You write the query text only — no explanation, no markdown fences, no commentary.

Rules:
- Output must be valid query text for the given data source syntax (SQL, YAML, JSON, GraphQL, Python, etc.).
- Use table and column names from the provided schema when available; do not invent names if schema is present.
- Follow the query runner documentation exactly for non-SQL data sources.
- If an existing query is provided, refine or extend it according to the request unless the user asks for something unrelated.
- Prefer readable formatting with sensible line breaks.
- Do not wrap the answer in ``` code blocks.
- Return only the query text."""


def _client() -> OpenAI:
    if not settings.OPENAI_API_KEY:
        raise RuntimeError("OpenAI API key is not configured")
    return OpenAI(api_key=settings.OPENAI_API_KEY)


def _extract_query_text(content: str) -> str:
    content = (content or "").strip()
    if not content:
        return content

    fence_match = re.match(r"^```(?:\w+)?\s*\n(.*)\n```\s*$", content, re.DOTALL)
    if fence_match:
        return fence_match.group(1).strip()

    if content.startswith("```"):
        lines = content.split("\n")
        if lines[0].startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]
        return "\n".join(lines).strip()

    return content


def _format_schema(schema: list[Any]) -> str:
    if not schema:
        return ""

    lines: list[str] = []
    for table in schema[:_MAX_SCHEMA_TABLES]:
        if not isinstance(table, dict):
            continue
        table_name = table.get("name")
        if not table_name:
            continue
        columns = table.get("columns") or []
        column_names: list[str] = []
        for column in columns[:_MAX_SCHEMA_COLUMNS]:
            if isinstance(column, dict):
                name = column.get("name")
                col_type = column.get("type")
                column_names.append(f"{name} ({col_type})" if col_type else str(name))
            else:
                column_names.append(str(column))
        lines.append(f"- {table_name}: {', '.join(column_names)}")

    return "\n".join(lines)


def _runner_context(data_source_type: str, syntax: str) -> str:
    runner_summary = summarize_runner_for_type(data_source_type) or {}
    runner_docs = get_query_runner_type(data_source_type)
    parts = [
        f"Data source type: {data_source_type}",
        f"Query syntax: {syntax or runner_summary.get('syntax', 'sql')}",
    ]

    summary = runner_summary.get("summary") or runner_docs.get("syntax_guide", {}).get("summary")
    if summary:
        parts.append(f"Summary: {summary}")

    tips = runner_summary.get("tips") or []
    if tips:
        parts.append("Tips:\n" + "\n".join(f"- {tip}" for tip in tips[:6]))

    type_notes = runner_docs.get("type_notes") or {}
    example_query = type_notes.get("example_query")
    if example_query:
        parts.append(f"Example query:\n{example_query}")

    return "\n".join(parts)


def generate_query(
    *,
    prompt: str,
    data_source_type: str,
    data_source_name: str,
    syntax: str,
    schema: Optional[list[Any]] = None,
    existing_query: Optional[str] = None,
) -> str:
    """Turn a natural-language request into query text for the active data source."""
    prompt = (prompt or "").strip()
    if not prompt:
        raise ValueError("prompt is required")

    schema_text = _format_schema(schema or [])
    user_parts = [
        f"Data source: {data_source_name}",
        _runner_context(data_source_type, syntax),
        f"User request: {prompt}",
    ]

    if schema_text:
        user_parts.append(f"Schema:\n{schema_text}")

    existing_query = (existing_query or "").strip()
    if existing_query:
        user_parts.append(f"Current query:\n{existing_query}")

    user_parts.append("Write the query text:")

    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": "\n\n".join(user_parts)},
    ]

    kwargs: dict[str, Any] = {
        "model": settings.OPENAI_MODEL,
        "messages": messages,
        "temperature": 0.2,
    }
    if settings.OPENAI_REASONING_EFFORT:
        kwargs["reasoning_effort"] = settings.OPENAI_REASONING_EFFORT

    client = _client()
    last_error: Optional[Exception] = None
    for attempt in range(_MAX_API_ATTEMPTS):
        try:
            response = client.chat.completions.create(**kwargs)
            content = response.choices[0].message.content or ""
            query_text = _extract_query_text(content)
            if not query_text:
                raise RuntimeError("The AI returned an empty query.")
            return query_text
        except _RETRYABLE_ERRORS as exc:
            last_error = exc
            logger.warning("Query generation OpenAI transient error (attempt %s): %s", attempt + 1, exc)
            if attempt < _MAX_API_ATTEMPTS - 1:
                continue

    raise last_error or RuntimeError("Query generation failed")
