"""OpenAI chat loop with tool execution."""

from __future__ import annotations

import json
import logging
from typing import Any

from openai import OpenAI

from redash import settings
from redash.assistant.tools import TOOL_DEFINITIONS, ToolContext, execute_tool

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """You are Rewatch Assistant, an expert helper embedded in the Rewatch data platform (a Redash fork).

You help users:
- Explore and explain query data (run queries, summarize results, spot trends)
- Write and create SQL queries against their connected data sources
- Create and update dashboards and alerts
- Answer how-to questions using the documentation tools

Guidelines:
- Use tools to fetch real data instead of guessing. When explaining query results, summarize clearly and cite column names and sample values.
- Before creating queries, list data sources or inspect schema when table/column names are unknown.
- When creating alerts, confirm the query exists and pick a sensible column from its result set.
- For documentation questions, search_docs first, then get_docs_topic for details. Share the doc URL with the user.
- Be concise but thorough. Use markdown for formatting when helpful.
- If a tool returns an error, explain it plainly and suggest a fix.
"""


def _client() -> OpenAI:
    if not settings.OPENAI_API_KEY:
        raise RuntimeError("OpenAI API key is not configured")
    return OpenAI(api_key=settings.OPENAI_API_KEY)


def chat(
    *,
    messages: list[dict[str, Any]],
    base_url: str,
    api_key: str,
    help_base_url: str,
) -> dict[str, Any]:
    """Run the assistant chat loop. Returns reply text and updated message history."""
    ctx = ToolContext(base_url=base_url, api_key=api_key, help_base_url=help_base_url)
    client = _client()

    conversation: list[dict[str, Any]] = [{"role": "system", "content": SYSTEM_PROMPT}]
    conversation.extend(messages)

    max_rounds = 12
    for _ in range(max_rounds):
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
                logger.info("Assistant tool call: %s(%s)", fn_name, fn_args)
                result = execute_tool(ctx, fn_name, fn_args)
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
        # Return only user/assistant messages (no system/tools) for client persistence.
        client_messages = [m for m in conversation if m["role"] in ("user", "assistant") and m.get("content")]
        return {"reply": reply, "messages": client_messages}

    raise RuntimeError("Assistant exceeded maximum tool rounds")
