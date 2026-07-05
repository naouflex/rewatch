"""OpenAI chat loop with tool execution."""

from __future__ import annotations

import json
import logging
import time
from typing import Any, Callable, Optional

from openai import (
    APIConnectionError,
    APITimeoutError,
    InternalServerError,
    OpenAI,
    RateLimitError,
)

from redash import settings
from redash.assistant.activity import tool_start_label
from redash.assistant.links import append_preview_markdown, collect_previews, normalize_reply_links
from redash.assistant.tools import TOOL_DEFINITIONS, ToolContext, execute_tool

logger = logging.getLogger(__name__)

ActivityCallback = Callable[[dict[str, Any]], None]

SYSTEM_PROMPT = """You are Rewatch Assistant, an expert helper embedded in the Rewatch data platform.

You help users:
- Explore and explain query data (run queries, summarize results, spot trends)
- Write and create SQL queries against their connected data sources
- Create and configure visualizations (charts, counters, tables) on queries
- Build dashboards: create dashboards, add widgets, arrange layout
- Create and manage alerts and notification destinations
- Work with ML models, predictions, and indexers (Rewatch extensions)
- Search the public web and read documentation pages when Rewatch data or docs are not enough
- Answer how-to questions using the documentation tools

Guidelines:
- Use tools to fetch real data instead of guessing. When explaining query results, summarize clearly and cite column names and sample values.
- Platform catalog (use proactively — do not guess query or visualization syntax):
  - list_data_sources returns each source's `type` and a `query_runner` summary (syntax + tips).
  - Before writing query text for any unfamiliar data source type, call get_query_runner_type with that `type`.
  - Before create_visualization, call get_visualization_type for the target type (CHART, MAP, CHOROPLETH, etc.).
  - list_query_runner_types / list_visualization_types browse everything the platform supports.
- When the user asks to create a query and the data source is not specified, call list_data_sources first and pick the best match by type/name. Never ask the user which data source to use if one is available.
- SQL data sources: use get_data_source_schema when table/column names are unknown.
- Non-SQL data sources: follow get_query_runner_type docs exactly (YAML, JSON, GraphQL, Python, etc.). Test with run_query (ad-hoc query_text) before create_query.
- For public HTTP/JSON datasets: web_search + fetch_url to find real endpoints — never invent sample data.
- create_query and update_query automatically execute query text before saving and again after saving. Always read the validation block in the tool response:
  - If validation status is error, fix the query using the error message, schema, and sample data, then update_query. Never tell the user a broken query succeeded.
  - If status is needs_parameters, ask the user for parameter values or use run_query with parameters before continuing.
  - If validation includes action_required, call update_query to fix the saved query — do not create a duplicate query.
  - Use validation columns/rows when building chart columnMapping.
- When exploring unfamiliar data, use run_query with ad-hoc query_text first, then create_query once validation succeeds.
- New queries get a default Table visualization automatically. For other visualizations, consult get_visualization_type and use validation columns in options.
- To put a chart on a dashboard: create_visualization → add_widget_to_dashboard with visualization_id.
  Use get_dashboard to read the current layout; widget options use col, row, sizeX, sizeY grid units.
- When creating alerts, confirm the query exists and pick a sensible column from its result set.
- ML training and prediction are asynchronous — tell the user to check back or use get_predictions.
- For Rewatch how-to questions, search_docs first, then get_docs_topic for details.
- For external APIs, libraries, SQL dialects, or current events, use web_search then fetch_url on the best results.
- Cite URLs when using information from the web.
- After creating or changing resources, share direct links using app_link from tool results, or path-based URLs like /queries/{id} and /dashboards/{id}-{slug}.
- When tool results include preview_image_url, show the preview in chat using markdown images, e.g. ![Query name](preview_image_url). Previews are auto-appended when you forget.
- Rewatch uses path-based routing. Never use hash URLs (wrong: /#/queries/5 or {base_url}/#/queries/5; correct: /queries/5 or {base_url}/queries/5).
- Be proactive: when the user says "yes" or agrees to a plan, execute it with tools immediately — do not re-ask for names, URLs, or data sources you can infer or discover.
- If a tool returns an error, explain it plainly and suggest a fix.
"""


def _client() -> OpenAI:
    if not settings.OPENAI_API_KEY:
        raise RuntimeError("OpenAI API key is not configured")
    return OpenAI(api_key=settings.OPENAI_API_KEY)


_RETRYABLE_ERRORS = (RateLimitError, APIConnectionError, APITimeoutError, InternalServerError)
_MAX_API_ATTEMPTS = 3


def _stream_completion(
    client: OpenAI,
    conversation: list[dict[str, Any]],
    on_activity: Optional[ActivityCallback],
    *,
    tool_choice: str = "auto",
) -> dict[str, Any]:
    """Stream one completion, emitting reply text deltas as they arrive.

    Returns {"content": str, "tool_calls": [{"id", "name", "arguments"}, ...]}.
    Retries transient API errors with backoff.
    """
    kwargs: dict[str, Any] = {
        "model": settings.OPENAI_MODEL,
        "messages": conversation,
        "tools": TOOL_DEFINITIONS,
        "tool_choice": tool_choice,
        "stream": True,
    }
    if settings.OPENAI_REASONING_EFFORT:
        kwargs["reasoning_effort"] = settings.OPENAI_REASONING_EFFORT

    last_error: Optional[Exception] = None
    for attempt in range(_MAX_API_ATTEMPTS):
        content_parts: list[str] = []
        tool_calls: dict[int, dict[str, str]] = {}
        emitted_any_delta = False
        try:
            stream = client.chat.completions.create(**kwargs)
            for chunk in stream:
                if not chunk.choices:
                    continue
                delta = chunk.choices[0].delta
                if delta is None:
                    continue
                if delta.content:
                    content_parts.append(delta.content)
                    emitted_any_delta = True
                    _emit(on_activity, {"type": "reply_delta", "text": delta.content})
                for tc in delta.tool_calls or []:
                    entry = tool_calls.setdefault(tc.index, {"id": "", "name": "", "arguments": ""})
                    if tc.id:
                        entry["id"] = tc.id
                    if tc.function:
                        if tc.function.name:
                            entry["name"] = tc.function.name
                        if tc.function.arguments:
                            entry["arguments"] += tc.function.arguments
            return {
                "content": "".join(content_parts),
                "tool_calls": [tool_calls[i] for i in sorted(tool_calls)],
            }
        except _RETRYABLE_ERRORS as exc:
            last_error = exc
            # If tokens already reached the client we can't cleanly retry the
            # same turn — surface the error instead of duplicating output.
            if emitted_any_delta:
                raise
            if attempt < _MAX_API_ATTEMPTS - 1:
                wait = 2**attempt
                logger.warning("Assistant OpenAI transient error (attempt %s): %s", attempt + 1, exc)
                _emit(on_activity, {"type": "status", "message": "AI service hiccup — retrying…"})
                time.sleep(wait)

    raise last_error  # type: ignore[misc]


def _emit(on_activity: Optional[ActivityCallback], event: dict[str, Any]) -> None:
    if on_activity:
        on_activity(event)


def _emit_validation_status(on_activity: Optional[ActivityCallback], payload: Any) -> None:
    if not on_activity or not isinstance(payload, dict):
        return

    validation = payload.get("validation")
    if isinstance(validation, dict):
        if "post_save" in validation or "pre_save" in validation:
            for key in ("post_save", "pre_save"):
                check = validation.get(key) or {}
                status = check.get("status")
                if status == "error":
                    message = check.get("message") or "Unknown error"
                    _emit(on_activity, {"type": "status", "message": f"Query validation failed: {message[:120]}"})
                    return
                if status == "ok":
                    _emit(on_activity, {"type": "status", "message": "Query validation passed."})
                    return
            return

        status = validation.get("status")
        if status == "ok":
            _emit(on_activity, {"type": "status", "message": "Query validation passed."})
        elif status == "error":
            message = validation.get("message") or "Unknown error"
            _emit(on_activity, {"type": "status", "message": f"Query validation failed: {message[:120]}"})

    query_validation = payload.get("query_validation")
    if isinstance(query_validation, dict):
        status = query_validation.get("status")
        if status == "ok":
            _emit(on_activity, {"type": "status", "message": "Query validation passed."})
        elif status == "error":
            message = query_validation.get("message") or "Unknown error"
            _emit(on_activity, {"type": "status", "message": f"Query validation failed: {message[:120]}"})


def chat(
    *,
    messages: list[dict[str, Any]],
    base_url: str,
    api_key: str,
    help_base_url: str,
    on_activity: Optional[ActivityCallback] = None,
) -> dict[str, Any]:
    """Run the assistant chat loop. Returns reply text and updated message history."""
    ctx = ToolContext(base_url=base_url, api_key=api_key, help_base_url=help_base_url)
    client = _client()
    web_base = base_url.rstrip("/")

    conversation: list[dict[str, Any]] = [
        {"role": "system", "content": SYSTEM_PROMPT.replace("{base_url}", web_base)},
    ]
    conversation.extend(messages)

    _emit(on_activity, {"type": "status", "message": "Analyzing your request…"})

    max_rounds = 18
    collected_previews: list[dict[str, str]] = []
    for round_idx in range(max_rounds + 1):
        if round_idx > 0:
            _emit(on_activity, {"type": "status", "message": "Planning next step…"})

        # Past the round budget, force a text answer so the user always gets
        # a summary of progress instead of a hard failure.
        final_round = round_idx == max_rounds
        if final_round:
            conversation.append(
                {
                    "role": "system",
                    "content": (
                        "Tool budget exhausted. Do not call more tools. Summarize what was "
                        "accomplished so far, what remains, and how the user can continue."
                    ),
                }
            )

        try:
            turn = _stream_completion(
                client,
                conversation,
                on_activity,
                tool_choice="none" if final_round else "auto",
            )
        except Exception as exc:
            logger.exception("Assistant OpenAI request failed")
            fallback = (
                "Sorry, I ran into an error talking to the AI service. "
                f"Please try again. ({exc})"
            )
            return {"reply": fallback, "messages": messages + [{"role": "assistant", "content": fallback}]}

        if turn["tool_calls"]:
            # Interim content preceding tool calls is not the final reply —
            # tell the client to clear any streamed draft.
            _emit(on_activity, {"type": "reply_reset"})
            conversation.append(
                {
                    "role": "assistant",
                    "content": turn["content"] or "",
                    "tool_calls": [
                        {
                            "id": tc["id"],
                            "type": "function",
                            "function": {"name": tc["name"], "arguments": tc["arguments"]},
                        }
                        for tc in turn["tool_calls"]
                    ],
                }
            )
            for tool_call in turn["tool_calls"]:
                fn_name = tool_call["name"]
                try:
                    fn_args = json.loads(tool_call["arguments"] or "{}")
                except json.JSONDecodeError:
                    fn_args = {}

                label = tool_start_label(fn_name, fn_args)
                activity_id = tool_call["id"]
                _emit(
                    on_activity,
                    {"type": "tool_start", "id": activity_id, "tool": fn_name, "label": label},
                )
                logger.info("Assistant tool call: %s(%s)", fn_name, fn_args)

                result = execute_tool(ctx, fn_name, fn_args)
                try:
                    payload = json.loads(result)
                    collected_previews.extend(collect_previews(payload))
                    _emit_validation_status(on_activity, payload)
                except (json.JSONDecodeError, TypeError, AttributeError) as exc:
                    logger.warning("Assistant post-tool processing failed for %s: %s", fn_name, exc)
                _emit(
                    on_activity,
                    {"type": "tool_done", "id": activity_id, "tool": fn_name, "label": label},
                )
                conversation.append(
                    {
                        "role": "tool",
                        "tool_call_id": tool_call["id"],
                        "content": result,
                    }
                )
            continue

        try:
            reply = normalize_reply_links(turn["content"] or "")
            reply = append_preview_markdown(reply, collected_previews)
        except Exception as exc:
            logger.exception("Assistant reply formatting failed")
            reply = (turn["content"] or "").strip() or f"I finished the requested actions but hit a formatting error: {exc}"
        conversation.append({"role": "assistant", "content": reply})
        client_messages = [m for m in conversation if m["role"] in ("user", "assistant") and m.get("content")]
        return {"reply": reply, "messages": client_messages}

    raise RuntimeError("Assistant exceeded maximum tool rounds")
