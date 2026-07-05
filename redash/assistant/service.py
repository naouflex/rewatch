"""OpenAI chat loop with tool execution."""

from __future__ import annotations

import json
import logging
from typing import Any, Callable, Optional

from openai import OpenAI

from redash import settings
from redash.assistant.activity import tool_start_label
from redash.assistant.tools import TOOL_DEFINITIONS, ToolContext, execute_tool

logger = logging.getLogger(__name__)

ActivityCallback = Callable[[dict[str, Any]], None]

SYSTEM_PROMPT = """You are Rewatch Assistant, an expert helper embedded in the Rewatch data platform (a Redash fork).

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
- Before creating queries, list data sources or inspect schema when table/column names are unknown.
- New queries get a default Table visualization automatically. For charts, use create_visualization with type CHART:
  - Run the query first to learn column names.
  - Set options.columnMapping (e.g. {"date_col": "x", "metric_col": "y"}).
  - Set options.globalSeriesType: column, line, bar, area, pie, or scatter.
- To put a chart on a dashboard: create_visualization → add_widget_to_dashboard with visualization_id.
  Use get_dashboard to read the current layout; widget options use col, row, sizeX, sizeY grid units.
- When creating alerts, confirm the query exists and pick a sensible column from its result set.
- ML training and prediction are asynchronous — tell the user to check back or use get_predictions.
- For Rewatch how-to questions, search_docs first, then get_docs_topic for details.
- For external APIs, libraries, SQL dialects, or current events, use web_search then fetch_url on the best results.
- Cite URLs when using information from the web.
- After creating or changing resources, share direct links (e.g. /queries/{id}, /dashboards/{slug}).
- Be concise but thorough. Use markdown for formatting when helpful.
- If a tool returns an error, explain it plainly and suggest a fix.
"""


def _client() -> OpenAI:
    if not settings.OPENAI_API_KEY:
        raise RuntimeError("OpenAI API key is not configured")
    return OpenAI(api_key=settings.OPENAI_API_KEY)


def _emit(on_activity: Optional[ActivityCallback], event: dict[str, Any]) -> None:
    if on_activity:
        on_activity(event)


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

    conversation: list[dict[str, Any]] = [{"role": "system", "content": SYSTEM_PROMPT}]
    conversation.extend(messages)

    _emit(on_activity, {"type": "status", "message": "Analyzing your request…"})

    max_rounds = 18
    for round_idx in range(max_rounds):
        if round_idx > 0:
            _emit(on_activity, {"type": "status", "message": "Planning next step…"})

        response = client.chat.completions.create(
            model=settings.OPENAI_MODEL,
            messages=conversation,
            tools=TOOL_DEFINITIONS,
            tool_choice="auto",
        )
        choice = response.choices[0].message

        if choice.tool_calls:
            conversation.append(
                {
                    "role": "assistant",
                    "content": choice.content or "",
                    "tool_calls": [
                        {
                            "id": tc.id,
                            "type": "function",
                            "function": {"name": tc.function.name, "arguments": tc.function.arguments},
                        }
                        for tc in choice.tool_calls
                    ],
                }
            )
            for tool_call in choice.tool_calls:
                fn_name = tool_call.function.name
                try:
                    fn_args = json.loads(tool_call.function.arguments or "{}")
                except json.JSONDecodeError:
                    fn_args = {}

                label = tool_start_label(fn_name, fn_args)
                activity_id = tool_call.id
                _emit(
                    on_activity,
                    {"type": "tool_start", "id": activity_id, "tool": fn_name, "label": label},
                )
                logger.info("Assistant tool call: %s(%s)", fn_name, fn_args)

                result = execute_tool(ctx, fn_name, fn_args)
                _emit(
                    on_activity,
                    {"type": "tool_done", "id": activity_id, "tool": fn_name, "label": label},
                )
                conversation.append(
                    {
                        "role": "tool",
                        "tool_call_id": tool_call.id,
                        "content": result,
                    }
                )
            continue

        reply = choice.content or ""
        conversation.append({"role": "assistant", "content": reply})
        _emit(on_activity, {"type": "status", "message": "Composing reply…"})
        client_messages = [m for m in conversation if m["role"] in ("user", "assistant") and m.get("content")]
        return {"reply": reply, "messages": client_messages}

    raise RuntimeError("Assistant exceeded maximum tool rounds")
