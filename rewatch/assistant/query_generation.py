"""Generate query text from natural language for the query editor."""

from __future__ import annotations

import logging
import re
from typing import Any, Optional

from openai import OpenAI

from rewatch import settings
from rewatch.assistant.openai_retry import call_with_retry, create_openai_client
from rewatch.assistant.catalog import build_query_generation_context

logger = logging.getLogger(__name__)

_MAX_SCHEMA_TABLES = 50
_MAX_SCHEMA_COLUMNS = 20
_MAX_DYNAMIC_SCHEMA_ITEMS = 15
_MAX_COIN_SAMPLES = 12


def _system_prompt(syntax: str) -> str:
    syntax = (syntax or "sql").lower()
    base = """You are a query authoring assistant embedded in Rewatch (a data platform).

The user describes what they want in plain language. You write the query text only — no explanation, no markdown fences, no commentary.

General rules:
- Output must match the data source's query syntax exactly (see Query syntax and Generation rules below).
- Use schema entries and example queries as templates — do not invent table names, endpoints, or API URLs.
- If schema lists YAML templates (insertValue), follow their key structure and naming.
- If an existing query is provided, refine or extend it unless the user asks for something unrelated.
- Prefer readable formatting with sensible line breaks.
- Do not wrap the answer in ``` code blocks.
- Return only the query text."""

    syntax_specific = {
        "yaml": "\n- This data source uses YAML query syntax — never output SQL or JSON.",
        "json": "\n- This data source uses JSON query syntax — never output SQL or YAML.",
        "graphql": "\n- Output a GraphQL query/mutation string only.",
        "python": "\n- Output executable Python script text only.",
        "sql": "\n- Output SQL only. Use table/column names from schema.",
    }
    return base + syntax_specific.get(syntax, "")


def _client() -> OpenAI:
    return create_openai_client()


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


def _is_dynamic_schema_entry(name: str) -> bool:
    """Large runtime-populated categories (e.g. coins.bitcoin)."""
    return name.startswith("coins.")


def _format_schema_table(table: dict[str, Any], syntax: str) -> list[str]:
    table_name = table.get("name")
    if not table_name:
        return []

    display_name = table.get("displayName")
    description = table.get("description")
    insert_value = (table.get("insertValue") or "").strip()
    columns = table.get("columns") or []

    lines: list[str] = []
    label = f"{table_name} ({display_name})" if display_name and display_name != table_name else str(table_name)
    if description:
        label = f"{label} — {description}"
    lines.append(f"- {label}")

    if insert_value and syntax == "yaml":
        lines.append("  Template:")
        for template_line in insert_value.splitlines():
            lines.append(f"    {template_line}")
    elif columns:
        column_bits: list[str] = []
        for column in columns[:_MAX_SCHEMA_COLUMNS]:
            if isinstance(column, dict):
                col_name = column.get("name")
                col_type = column.get("type")
                col_desc = column.get("description")
                bit = f"{col_name} ({col_type})" if col_type else str(col_name)
                if col_desc:
                    bit = f"{bit}: {col_desc}"
                column_bits.append(bit)
            else:
                column_bits.append(str(column))
        if column_bits:
            lines.append(f"  Columns: {', '.join(column_bits)}")

    return lines


def _format_schema(schema: list[Any], syntax: str = "sql") -> str:
    if not schema:
        return ""

    endpoint_entries: list[dict[str, Any]] = []
    dynamic_entries: list[dict[str, Any]] = []
    sql_entries: list[dict[str, Any]] = []

    for table in schema:
        if not isinstance(table, dict):
            continue
        name = table.get("name") or ""
        if _is_dynamic_schema_entry(name):
            dynamic_entries.append(table)
        elif table.get("insertValue") or "." in name:
            endpoint_entries.append(table)
        else:
            sql_entries.append(table)

    lines: list[str] = []

    for table in endpoint_entries[:_MAX_SCHEMA_TABLES]:
        lines.extend(_format_schema_table(table, syntax))

    for table in sql_entries[:_MAX_SCHEMA_TABLES]:
        lines.extend(_format_schema_table(table, syntax))

    if dynamic_entries:
        samples = dynamic_entries[:_MAX_COIN_SAMPLES]
        sample_names = [
            (entry.get("displayName") or entry.get("name", "").split(".", 1)[-1]) for entry in samples
        ]
        lines.append(
            f"- coins.* ({len(dynamic_entries)} popular coins in schema, e.g. {', '.join(sample_names)})"
        )
        lines.append("  Use coingeckoID from a coins.* template when querying a specific coin.")
        for table in samples[:5]:
            insert_value = (table.get("insertValue") or "").strip()
            if insert_value:
                display = table.get("displayName") or table.get("name")
                lines.append(f"  Example ({display}):")
                for template_line in insert_value.splitlines():
                    lines.append(f"    {template_line}")

    return "\n".join(lines)


def _format_endpoint_catalog(catalog: list[dict[str, Any]]) -> str:
    if not catalog:
        return ""

    lines: list[str] = []
    current_category = None
    for entry in catalog:
        category = entry.get("category") or "other"
        if category != current_category:
            current_category = category
            lines.append(f"[{category}]")
        endpoint = entry.get("endpoint")
        description = entry.get("description") or ""
        path_params = entry.get("path_params") or []
        param_hint = f" (params: {', '.join(path_params)})" if path_params else ""
        pro_hint = " [Pro]" if entry.get("pro_only") else ""
        lines.append(f"- {endpoint}{param_hint}{pro_hint}: {description}")
        example_query = (entry.get("example_query") or "").strip()
        if example_query:
            for template_line in example_query.splitlines():
                lines.append(f"    {template_line}")
    return "\n".join(lines)


def _runner_context(data_source_type: str, syntax: str) -> str:
    ctx = build_query_generation_context(data_source_type, syntax)
    parts = [
        f"Data source type: {ctx.get('type', data_source_type)} ({ctx.get('name', data_source_type)})",
        f"Query syntax: {ctx.get('syntax_label', syntax or 'sql')} ({ctx.get('syntax', syntax or 'sql')})",
    ]

    summary = ctx.get("summary")
    if summary:
        parts.append(f"Summary: {summary}")

    query_keys = ctx.get("query_keys") or []
    if query_keys:
        parts.append(f"Query keys: {', '.join(query_keys)}")

    config_notes = ctx.get("config_notes")
    if config_notes:
        parts.append(f"Config: {config_notes}")

    generation_rules = ctx.get("generation_rules") or []
    if generation_rules:
        parts.append("Generation rules:\n" + "\n".join(f"- {rule}" for rule in generation_rules))

    tips = ctx.get("tips") or []
    if tips:
        parts.append("Tips:\n" + "\n".join(f"- {tip}" for tip in tips[:8]))

    examples = ctx.get("example_queries") or []
    if examples:
        formatted_examples = []
        for idx, example in enumerate(examples[:4], start=1):
            formatted_examples.append(f"Example {idx}:\n{example.rstrip()}")
        parts.append("\n\n".join(formatted_examples))

    endpoint_catalog = ctx.get("endpoint_catalog") or []
    catalog_text = _format_endpoint_catalog(endpoint_catalog)
    if catalog_text:
        parts.append(f"Available endpoints:\n{catalog_text}")

    schema_hint = ctx.get("schema_hint")
    if schema_hint:
        parts.append(schema_hint)

    return "\n\n".join(parts)


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

    resolved_syntax = syntax or build_query_generation_context(data_source_type, syntax).get("syntax", "sql")
    schema_text = _format_schema(schema or [], resolved_syntax)
    user_parts = [
        f"Data source: {data_source_name}",
        _runner_context(data_source_type, resolved_syntax),
        f"User request: {prompt}",
    ]

    if schema_text:
        user_parts.append(f"Schema (tables/endpoints available — use these names and templates):\n{schema_text}")

    existing_query = (existing_query or "").strip()
    if existing_query:
        user_parts.append(f"Current query:\n{existing_query}")

    user_parts.append("Write the query text:")

    messages = [
        {"role": "system", "content": _system_prompt(resolved_syntax)},
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

    def _generate() -> str:
        response = client.chat.completions.create(**kwargs)
        content = response.choices[0].message.content or ""
        query_text = _extract_query_text(content)
        if not query_text:
            raise RuntimeError("The AI returned an empty query.")
        return query_text

    return call_with_retry(_generate, log_label="Query generation OpenAI")
