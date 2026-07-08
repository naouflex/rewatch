"""OpenAI chat loop with tool execution."""

from __future__ import annotations

import json
import logging
from typing import Any, Callable, Optional

from openai import OpenAI

from rewatch import settings
from rewatch.assistant.openai_retry import call_with_retry, create_openai_client
from rewatch.assistant.activity import tool_result_summary, tool_start_label
from rewatch.assistant.decision_graph import DecisionGraph
from rewatch.assistant.links import append_preview_markdown, collect_previews, normalize_reply_links
from rewatch.assistant.page_context import format_page_context
from rewatch.assistant.session_context import extract_resource_ids_from_payload
from rewatch.assistant.skills_prompt import build_skills_prompt
from rewatch.assistant.tools import TOOL_DEFINITIONS, ToolContext, execute_tool

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
  - Use validation.columns and visualization_hints when building charts — never invent column names.
- When exploring unfamiliar data, use run_query with ad-hoc query_text first, then create_query once validation succeeds.
- New queries get a default Table visualization automatically. For CHART/COUNTER, omit options in create_visualization unless the user asks for a specific chart style (e.g. globalSeriesType only).
- Dashboard fast path (STRONGLY preferred for any dashboard with 3+ widgets):
  - Use build_dashboard_from_spec: one call validates every query, creates queries + visualizations + widgets, lays out the grid, and publishes. Explore data with run_query first, then emit the full spec.
  - Multi-phase data: give base queries a `key`, then put aggregations in `derived` — their SQL references base results as {{cached_query.KEY}} tables on the Query Results source. Derived SQL runs on SQLite: no ::numeric or other PostgreSQL casts; use ROUND(x, 2), CAST(x AS INTEGER).
  - Use refresh_queries_and_wait before manually creating queries that read cached_query_{id} tables outside the builder.
  - Use create_multi_visualization_query for one wide summary row rendered as several KPI counters without a full dashboard.
  - Layout conventions the builder applies automatically: KPI counters 3x3 packed 4 per row, charts 6x8 side by side, tables full width 12x8, markdown section headers between groups. Pass role ("title", "section", "kpi", "half", "third", "full") or explicit position to override.
- Visualizations and dashboards (incremental playbook — for edits and small additions):
  - End-to-end: create_query (or use existing) → create_visualization → create_dashboard (if needed) → add_widget_to_dashboard → update_dashboard(is_draft=false) to publish.
  - Publish queries too: update_query(is_draft=false) once validation passes, so they are visible outside drafts.
  - For CHART/COUNTER/MAP: read visualization_hints.recommended from run_query or query_validation. Omit options in create_visualization — the server maps exact column names from query results.
  - columnMapping keys must match validation.columns exactly (including dots, e.g. market_cap.usd). Placeholders like date/tvl/x_column are wrong unless that literal name appears in columns.
  - If you must pass options, only set globalSeriesType or legend — not columnMapping. Wrong names are auto-corrected but omitting options is more reliable.
  - To fix broken charts on a query: call get_query(query_id) — it returns options_health per visualization and visualization_action_required when mappings are broken. Then call fix_query_visualizations(query_id) to auto-correct all charts in one step. For a single chart, use update_visualization(visualization_id) with default remap_columns=true.
  - When inspecting columns before fixing charts, use run_query(query_id, max_age=0) so cached results do not hide renamed columns.
  - Read column_corrections in create/update/fix responses to confirm what was remapped.
  - To edit charts: update_visualization (options/name). To edit dashboard layout: get_dashboard (read layout_summary + widget ids) → update_widget (options.position) or add_widget_to_dashboard / delete_widget.
  - Widget grid: 12 columns. options.position uses col (0–11), row, sizeX (width), sizeY (height). Full-width chart: sizeX=12. Side-by-side: two widgets with sizeX=6 on same row.
  - add_widget_to_dashboard auto-places below existing widgets when position is omitted.
  - Always get_dashboard after layout changes and share app_link. Publish drafts with update_dashboard(is_draft=false).
- When creating alerts, confirm the query exists and pick a sensible column from its result set.
- Alerts and notification destinations (follow this playbook):
  - End-to-end: run_query(query_id=...) → get_destination_type(type) → create_destination → create_alert(..., destination_ids=[...]).
  - Always validate the threshold column against run_query columns (create_alert does this automatically).
  - get_alert_template_guide lists Mustache variables (ALERT_NAME, QUERY_RESULT_VALUE, QUERY_RESULT_ROW, column shortcuts).
  - custom_subject / custom_body on the alert use Mustache. discord_webhook custom_body can be full Discord webhook JSON.
  - microsoft_teams_webhook uses destination options.message_template with {alert_name}, {alert_url} placeholders (not Mustache).
  - send_for_each_row: one notification per result row — use {{column_name}} and QUERY_RESULT_ROW in templates.
  - selector: first (default), min, or max across rows for threshold comparison.
  - subscribe_alert links an existing destination; create_alert destination_ids subscribes in one step.
  - evaluate_alert manually tests against latest query results.
- ML training and prediction are asynchronous — tell the user to check back or use get_predictions.
- For Rewatch how-to questions, search_docs first, then get_docs_topic for details.
- For endpoints not covered by dedicated tools, use list_endpoints / describe_endpoint / call_api (full REST API via OpenAPI spec).
- For dashboard inspiration, call list_dashboard_examples and get_dashboard_example before build_dashboard_from_spec.
- For analytics patterns (derived SQL, Python chaining, EVM logs/state, subgraph GraphQL, KPI counters), call list_instance_examples and get_instance_example — they reflect a production deployment with 500+ active queries.
- For external APIs, libraries, SQL dialects, or current events, use web_search then fetch_url on the best results.
- Cite URLs when using information from the web.
- After creating or changing resources, share direct links using app_link from tool results, or path-based URLs like /queries/{id} and /dashboards/{id}-{slug}.
- When tool results include preview_image_url, show the preview in chat using markdown images, e.g. ![Query name](preview_image_url). Previews are auto-appended when you forget.
- Rewatch uses path-based routing. Never use hash URLs (wrong: /#/queries/5 or {base_url}/#/queries/5; correct: /queries/5 or {base_url}/queries/5).
- Be proactive: when the user says "yes" or agrees to a plan, execute it with tools immediately — do not re-ask for names, URLs, or data sources you can infer or discover.
- When a "Current UI context" block is present, the user is on that page — treat referenced resource IDs as the subject of the conversation (e.g. "fix this query" means the active query_id).
- If a tool returns an error, explain it plainly and suggest a fix.
"""


def _client() -> OpenAI:
    return create_openai_client()


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
        "model": settings.ASSISTANT_OPENAI_MODEL,
        "messages": conversation,
        "tools": TOOL_DEFINITIONS,
        "tool_choice": tool_choice,
        "stream": True,
    }
    if settings.OPENAI_REASONING_EFFORT:
        kwargs["reasoning_effort"] = settings.OPENAI_REASONING_EFFORT

    emitted_any_delta = False

    def _consume_stream() -> dict[str, Any]:
        nonlocal emitted_any_delta
        emitted_any_delta = False
        content_parts: list[str] = []
        tool_calls: dict[int, dict[str, str]] = {}
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

    return call_with_retry(
        _consume_stream,
        on_status=on_activity,
        can_retry=lambda: not emitted_any_delta,
        log_label="Assistant OpenAI",
    )


def _emit(on_activity: Optional[ActivityCallback], event: dict[str, Any]) -> None:
    if on_activity:
        on_activity(event)


def _wrap_activity(graph: DecisionGraph, on_activity: Optional[ActivityCallback]) -> ActivityCallback:
    def callback(event: dict[str, Any]) -> None:
        event_type = event.get("type")
        if event_type == "status":
            graph.add_status(event.get("message") or "Working…")
        _emit(on_activity, event)

    return callback


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
    page_context: Optional[dict[str, Any]] = None,
    session_context: Optional[str] = None,
) -> dict[str, Any]:
    """Run the assistant chat loop. Returns reply text and updated message history."""
    ctx = ToolContext(base_url=base_url, api_key=api_key, help_base_url=help_base_url)
    client = _client()
    web_base = base_url.rstrip("/")

    system_content = SYSTEM_PROMPT.replace("{base_url}", web_base)
    skills_block = build_skills_prompt()
    if skills_block:
        system_content = f"{system_content}\n\n{skills_block}"
    if session_context:
        system_content = f"{system_content}\n\n{session_context}"
    page_block = format_page_context(page_context)
    if page_block:
        system_content = f"{system_content}\n\n{page_block}"

    conversation: list[dict[str, Any]] = [
        {"role": "system", "content": system_content},
    ]
    conversation.extend(messages)

    graph = DecisionGraph(on_activity=on_activity)
    graph.start("Analyzing your request…")
    activity = _wrap_activity(graph, on_activity)

    max_rounds = settings.ASSISTANT_MAX_TOOL_ROUNDS
    collected_previews: list[dict[str, str]] = []
    tool_graph_ids: dict[str, str] = {}
    for round_idx in range(max_rounds + 1):
        graph.start_step(round_idx)

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
                activity,
                tool_choice="none" if final_round else "auto",
            )
        except Exception as exc:
            logger.exception("Assistant OpenAI request failed")
            fallback = (
                "Sorry, I ran into an error talking to the AI service. "
                f"Please try again. ({exc})"
            )
            graph.complete(label="Error")
            return {
                "reply": fallback,
                "messages": messages + [{"role": "assistant", "content": fallback}],
                "decision_graph": graph.to_dict(),
            }

        if turn["tool_calls"]:
            # Interim content preceding tool calls is not the final reply —
            # tell the client to clear any streamed draft.
            _emit(activity, {"type": "reply_reset"})
            tool_names = [tc["name"] for tc in turn["tool_calls"]]
            graph.add_decision(
                label=f"Using {len(tool_names)} tool{'s' if len(tool_names) != 1 else ''}",
                detail=turn["content"] or None,
                tool_names=tool_names,
            )
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
                except json.JSONDecodeError as exc:
                    raw = (tool_call.get("arguments") or "")[:500]
                    err_result = json.dumps(
                        {
                            "error": (
                                f"Tool call {fn_name!r} had invalid JSON arguments: {exc}. "
                                f"Retry with valid JSON. Raw: {raw!r}"
                            )
                        }
                    )
                    _emit(
                        activity,
                        {
                            "type": "tool_done",
                            "id": tool_call["id"],
                            "tool": fn_name,
                            "label": f"Invalid arguments for {fn_name}",
                        },
                    )
                    graph_id = tool_graph_ids.get(tool_call["id"])
                    if graph_id:
                        graph.finish_tool(graph_id, error="Invalid tool arguments")
                    conversation.append(
                        {
                            "role": "tool",
                            "tool_call_id": tool_call["id"],
                            "content": err_result,
                        }
                    )
                    continue

                label = tool_start_label(fn_name, fn_args)
                activity_id = tool_call["id"]
                graph_id = graph.start_tool(
                    node_id=activity_id,
                    tool=fn_name,
                    label=label,
                    arguments=fn_args,
                )
                tool_graph_ids[activity_id] = graph_id
                _emit(
                    activity,
                    {"type": "tool_start", "id": activity_id, "tool": fn_name, "label": label},
                )
                logger.info("Assistant tool call: %s(%s)", fn_name, fn_args)

                result = execute_tool(ctx, fn_name, fn_args)
                result_summary = None
                try:
                    payload = json.loads(result)
                    collected_previews.extend(collect_previews(payload))
                    _emit_validation_status(activity, payload)
                    result_summary = tool_result_summary(fn_name, payload)
                    resource_ids = extract_resource_ids_from_payload(payload)
                    if isinstance(payload, dict) and payload.get("error"):
                        graph.finish_tool(
                            graph_id,
                            label=label,
                            result_summary=result_summary,
                            error=str(payload["error"]),
                            resource_ids=resource_ids or None,
                        )
                    else:
                        graph.finish_tool(
                            graph_id,
                            label=label,
                            result_summary=result_summary,
                            resource_ids=resource_ids or None,
                        )
                except (json.JSONDecodeError, TypeError, AttributeError) as exc:
                    logger.warning("Assistant post-tool processing failed for %s: %s", fn_name, exc)
                    graph.finish_tool(graph_id, label=label, error=str(exc))
                _emit(
                    activity,
                    {"type": "tool_done", "id": activity_id, "tool": fn_name, "label": label},
                )
                conversation.append(
                    {
                        "role": "tool",
                        "tool_call_id": tool_call["id"],
                        "content": result,
                    }
                )
            graph.finish_step()
            continue

        compose_id = graph.add_decision(label="Composing final reply", detail=turn["content"] or None)
        graph.finish_step()
        try:
            reply = normalize_reply_links(turn["content"] or "")
            reply = append_preview_markdown(reply, collected_previews)
        except Exception as exc:
            logger.exception("Assistant reply formatting failed")
            reply = (turn["content"] or "").strip() or f"I finished the requested actions but hit a formatting error: {exc}"
        conversation.append({"role": "assistant", "content": reply})
        graph.complete(label="Reply sent", parent_id=compose_id)
        client_messages = [m for m in conversation if m["role"] in ("user", "assistant") and m.get("content")]
        return {"reply": reply, "messages": client_messages, "decision_graph": graph.to_dict()}

    raise RuntimeError("Assistant exceeded maximum tool rounds")
