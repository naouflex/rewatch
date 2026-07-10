"""OpenAI tool definitions and execution against the Rewatch API."""

from __future__ import annotations

import json
import logging
import time
from typing import Any, Callable, Optional

import requests

from rewatch.assistant.llm_config import (
    assistant_max_llm_chars,
    assistant_max_llm_messages,
    assistant_max_tool_result_chars,
)
from rewatch.assistant import api_meta
from rewatch.assistant import catalog as platform_catalog
from rewatch.assistant import alert_catalog
from rewatch.assistant import dashboard_builder
from rewatch.assistant import dashboard_examples
from rewatch.assistant import instance_examples
from rewatch.assistant import docs as docs_catalog
from rewatch.assistant import web as web_tools
from rewatch.assistant.dashboard_layout import (
    enrich_dashboard_for_assistant,
    has_explicit_position,
    normalize_widget_options,
    prepare_widget_options,
    prepare_widget_options_for_update,
    suggest_next_position,
    summarize_dashboard_layout,
    summarize_dashboard_layout,
)
from rewatch.assistant.datasources import enrich_data_source, enrich_data_sources
from rewatch.assistant.links import enrich_tool_payload
from rewatch.assistant.visualization_helpers import (
    build_visualization_hints,
    enrich_visualizations_for_assistant,
    normalize_visualization_options,
    suggest_visualization_options,
)

logger = logging.getLogger(__name__)

JOB_FINISHED = 3
JOB_FAILED = 4
JOB_CANCELED = 5


def _as_dict(value: Any, label: str = "response") -> dict[str, Any]:
    if isinstance(value, dict):
        return value
    raise RuntimeError(f"Unexpected {label} type: {type(value).__name__}")


def _extract_query_result_rows(response: Any) -> tuple[list[str], list[dict[str, Any]]]:
    if not isinstance(response, dict):
        return [], []
    query_result = response.get("query_result")
    if not isinstance(query_result, dict):
        return [], []
    data = query_result.get("data")
    if not isinstance(data, dict):
        return [], []
    rows = data.get("rows") or []
    if not isinstance(rows, list):
        rows = []
    columns = []
    for column in data.get("columns") or []:
        if isinstance(column, dict) and column.get("name"):
            columns.append(column["name"])
    return columns, rows


def _merge_body(**kwargs) -> dict:
    return {k: v for k, v in kwargs.items() if v is not None}


def _require_catalog_result(result: Any, label: str = "lookup") -> Any:
    if isinstance(result, dict) and result.get("error"):
        known = result.get("known_types")
        suffix = f" Known types: {known[:25]}" if isinstance(known, list) and known else ""
        raise RuntimeError(f"{label} failed: {result['error']}{suffix}")
    return result


def _require_widget_content(visualization_id: Any, text: Any) -> None:
    if visualization_id is None and not text:
        raise RuntimeError("Provide visualization_id (chart/table widget) or text (text box widget).")


TOOL_DEFINITIONS: list[dict[str, Any]] = [
    # --- Queries ---
    {
        "type": "function",
        "function": {
            "name": "search_queries",
            "description": "Search saved queries by name, description, or SQL text.",
            "parameters": {
                "type": "object",
                "properties": {
                    "q": {"type": "string", "description": "Search term"},
                    "page_size": {"type": "integer", "default": 10},
                },
                "required": ["q"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_query",
            "description": (
                "Get a saved query including SQL, data source, parameters, schedule, and visualizations. "
                "Also runs the query (max_age=0) and returns validation.columns, visualization_hints, "
                "and per-visualization options_health showing broken column mappings."
            ),
            "parameters": {
                "type": "object",
                "properties": {"query_id": {"type": "integer"}},
                "required": ["query_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "run_query",
            "description": (
                "Execute a saved query or ad-hoc query text and return result rows. "
                "Use query_text + data_source_id to test before create_query. "
                "Query syntax depends on data source type — call get_query_runner_type first. "
                "When inspecting columns to fix visualizations, pass max_age=0 for fresh results."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "query_id": {"type": "integer", "description": "Saved query ID"},
                    "query_text": {"type": "string", "description": "Ad-hoc query text (syntax per get_query_runner_type)"},
                    "data_source_id": {"type": "integer", "description": "Required with query_text"},
                    "parameters": {"type": "object", "description": "Parameter values for parameterized queries"},
                    "max_age": {
                        "type": "integer",
                        "description": "Cache age in seconds; -1 any cache, 0 always execute",
                        "default": -1,
                    },
                    "max_rows": {"type": "integer", "default": 100},
                },
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "create_query",
            "description": (
                "Create a new saved query (starts as draft). Query syntax depends on data source type — "
                "call get_query_runner_type with the source type before writing `query`. "
                "Always call list_data_sources first to pick data_source_id. "
                "Query text is executed automatically before and after save; read validation for columns/sample rows."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "name": {"type": "string"},
                    "query": {"type": "string", "description": "Query text (syntax per get_query_runner_type)"},
                    "data_source_id": {"type": "integer"},
                    "description": {"type": "string"},
                    "schedule": {"type": "object"},
                    "tags": {"type": "array", "items": {"type": "string"}},
                },
                "required": ["name", "query", "data_source_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "update_query",
            "description": (
                "Update an existing saved query. When query text changes, it is executed automatically "
                "before and after save; the response includes validation results. "
                "Use get_query_runner_type if unsure of query syntax."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "query_id": {"type": "integer"},
                    "name": {"type": "string"},
                    "query": {"type": "string"},
                    "description": {"type": "string"},
                    "schedule": {"type": "object"},
                    "tags": {"type": "array", "items": {"type": "string"}},
                    "is_draft": {"type": "boolean"},
                },
                "required": ["query_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "archive_query",
            "description": "Archive (soft-delete) a saved query.",
            "parameters": {
                "type": "object",
                "properties": {"query_id": {"type": "integer"}},
                "required": ["query_id"],
            },
        },
    },
    # --- Visualizations ---
    {
        "type": "function",
        "function": {
            "name": "create_visualization",
            "description": (
                "Add a visualization to a query. For CHART/COUNTER/MAP/CHOROPLETH, omit options "
                "(or pass only globalSeriesType) — column names are auto-resolved from query results. "
                "If you pass columnMapping/counterColName, invalid names are corrected to actual columns. "
                "Read visualization_hints from run_query or query_validation before choosing types."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "query_id": {"type": "integer"},
                    "type": {"type": "string", "description": "Visualization type, e.g. CHART, COUNTER, TABLE"},
                    "name": {"type": "string"},
                    "options": {"type": "object", "description": "Visualization-specific options"},
                    "description": {"type": "string"},
                },
                "required": ["query_id", "type", "name"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "update_visualization",
            "description": (
                "Update a visualization's name, type, or options. By default remap_columns=true "
                "re-validates the parent query and auto-corrects column names in options against "
                "live query results (Date→date, FedFundsRate→FedFundsRate_lag_1, etc.). "
                "Pass remap_columns=false to change only name/type without touching options."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "visualization_id": {"type": "integer"},
                    "name": {"type": "string"},
                    "type": {"type": "string"},
                    "options": {"type": "object"},
                    "description": {"type": "string"},
                    "remap_columns": {
                        "type": "boolean",
                        "description": "When true (default), validate and fix column mappings from query results.",
                        "default": True,
                    },
                },
                "required": ["visualization_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_visualization",
            "description": (
                "Get one visualization with diagnostics: invalid column mappings, suggested options, "
                "and live query columns from the parent query."
            ),
            "parameters": {
                "type": "object",
                "properties": {"visualization_id": {"type": "integer"}},
                "required": ["visualization_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "fix_query_visualizations",
            "description": (
                "Fix all visualizations on a query by re-running it and auto-correcting column mappings "
                "in every CHART/COUNTER/MAP/CHOROPLETH visualization. Use when charts are empty or show "
                "wrong data after a query migration or column rename."
            ),
            "parameters": {
                "type": "object",
                "properties": {"query_id": {"type": "integer"}},
                "required": ["query_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "delete_visualization",
            "description": "Delete a visualization from a query.",
            "parameters": {
                "type": "object",
                "properties": {"visualization_id": {"type": "integer"}},
                "required": ["visualization_id"],
            },
        },
    },
    # --- Data sources ---
    {
        "type": "function",
        "function": {
            "name": "list_data_sources",
            "description": (
                "List connected data sources (id, name, type) with query_runner summary per type. "
                "Always call this before create_query when the data source is unknown."
            ),
            "parameters": {"type": "object", "properties": {}},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "list_query_runner_types",
            "description": (
                "List all query runner types the platform supports (syntax, summary). "
                "Use before writing queries for unfamiliar data source types."
            ),
            "parameters": {
                "type": "object",
                "properties": {"q": {"type": "string", "description": "Optional filter by name or type"}},
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_query_runner_type",
            "description": (
                "Describe a query runner type: syntax, config schema, example queries, and per-endpoint "
                "templates (endpoint_catalog.example_query). Call with the data source `type` from "
                "list_data_sources (e.g. coingecko, defillama, json, pg). For CoinGecko/DefiLlama use "
                "endpoint/coingeckoID YAML — not url/path/fields."
            ),
            "parameters": {
                "type": "object",
                "properties": {"type": {"type": "string", "description": "Query runner type string"}},
                "required": ["type"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "list_visualization_types",
            "description": "List visualization types (CHART, MAP, COUNTER, etc.) with summaries.",
            "parameters": {
                "type": "object",
                "properties": {"q": {"type": "string", "description": "Optional filter"}},
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_visualization_type",
            "description": (
                "Get required/common options for a visualization type before create_visualization."
            ),
            "parameters": {
                "type": "object",
                "properties": {"type": {"type": "string", "description": "Visualization type, e.g. CHART, MAP"}},
                "required": ["type"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_data_source",
            "description": (
                "Get one data source by id (type, options, query_runner catalog summary). "
                "Call get_query_runner_type with the same type for full query format docs."
            ),
            "parameters": {
                "type": "object",
                "properties": {"data_source_id": {"type": "integer"}},
                "required": ["data_source_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_data_source_schema",
            "description": "Get tables and columns for a data source.",
            "parameters": {
                "type": "object",
                "properties": {
                    "data_source_id": {"type": "integer"},
                    "refresh": {"type": "boolean", "description": "Bypass schema cache"},
                },
                "required": ["data_source_id"],
            },
        },
    },
    # --- Dashboards & widgets ---
    {
        "type": "function",
        "function": {
            "name": "list_dashboards",
            "description": "List or search dashboards.",
            "parameters": {
                "type": "object",
                "properties": {
                    "q": {"type": "string"},
                    "page_size": {"type": "integer", "default": 10},
                },
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_dashboard",
            "description": (
                "Get a dashboard with widgets, layout_summary (grid positions), and visualization links. "
                "Always call before rearranging widgets or editing an existing dashboard."
            ),
            "parameters": {
                "type": "object",
                "properties": {"dashboard_id": {"type": "integer"}},
                "required": ["dashboard_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "create_dashboard",
            "description": "Create a new dashboard (starts as draft with empty layout).",
            "parameters": {
                "type": "object",
                "properties": {"name": {"type": "string"}},
                "required": ["name"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "update_dashboard",
            "description": (
                "Update dashboard name, tags, draft/archived status, or layout. "
                "Set is_draft=false to publish when widgets are placed."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "dashboard_id": {"type": "integer"},
                    "name": {"type": "string"},
                    "layout": {"type": "array", "description": "Grid layout array from get_dashboard"},
                    "tags": {"type": "array", "items": {"type": "string"}},
                    "is_draft": {"type": "boolean"},
                    "is_archived": {"type": "boolean"},
                },
                "required": ["dashboard_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "add_widget_to_dashboard",
            "description": (
                "Add a visualization or text box to a dashboard. Pass visualization_id for charts/tables, "
                "or text for markdown. Position goes in options.position (col, row, sizeX, sizeY on a "
                "12-column grid). Omit position to auto-place below existing widgets."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "dashboard_id": {"type": "integer"},
                    "visualization_id": {"type": "integer"},
                    "text": {"type": "string", "description": "Text box content (markdown supported)"},
                    "options": {
                        "type": "object",
                        "description": (
                            "Widget options; use options.position or top-level col/row/sizeX/sizeY "
                            "(col 0–11, sizeX width up to 12, sizeY height in row units)"
                        ),
                    },
                    "width": {"type": "integer", "default": 1},
                },
                "required": ["dashboard_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "update_widget",
            "description": (
                "Update a dashboard widget: text (markdown text boxes), and/or options.position to "
                "move or resize (col, row, sizeX, sizeY). Call get_dashboard first for widget_id and "
                "current positions."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "widget_id": {"type": "integer"},
                    "text": {"type": "string", "description": "New markdown text (text-box widgets)"},
                    "options": {
                        "type": "object",
                        "description": "Widget options; merge position via options.position",
                    },
                },
                "required": ["widget_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "delete_widget",
            "description": "Remove a widget from a dashboard.",
            "parameters": {
                "type": "object",
                "properties": {"widget_id": {"type": "integer"}},
                "required": ["widget_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "build_dashboard_from_spec",
            "description": (
                "Build a complete dashboard in ONE call: validate + create + publish all queries, "
                "visualizations, and widgets from a declarative spec. PREFER THIS over separate "
                "create_query/create_visualization/add_widget_to_dashboard calls whenever a dashboard "
                "needs 3+ widgets. Every query is executed for validation first — nothing is created "
                "if any query fails. Use `derived` for queries that aggregate other queries' cached "
                "results: reference base queries as {{cached_query.KEY}} in derived query text (base "
                "queries need a `key`). Derived queries run on SQLite — no PostgreSQL casts like "
                "::numeric. Widgets are auto-placed on a 12-column grid with type-aware sizes "
                "(counters 3x3 packed 4 per row, charts 6x8, tables 12x8, text headers full width); "
                "pass position or role ('title', 'section', 'kpi', 'half', 'third', 'full') to override."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "name": {"type": "string", "description": "Dashboard name"},
                    "queries": {
                        "type": "array",
                        "description": "Base queries to create (validated before anything is saved)",
                        "items": {
                            "type": "object",
                            "properties": {
                                "key": {
                                    "type": "string",
                                    "description": "Short id so derived queries can reference {{cached_query.KEY}}",
                                },
                                "name": {"type": "string"},
                                "description": {"type": "string"},
                                "data_source_id": {"type": "integer"},
                                "query": {"type": "string", "description": "Query text (syntax per data source type)"},
                                "visualizations": {
                                    "type": "array",
                                    "items": {
                                        "type": "object",
                                        "properties": {
                                            "type": {"type": "string", "description": "TABLE, CHART, COUNTER, MAP, ..."},
                                            "name": {"type": "string"},
                                            "chart_type": {
                                                "type": "string",
                                                "description": "For CHART: line, column, bar, area, pie, scatter",
                                            },
                                            "column_mapping": {
                                                "type": "object",
                                                "description": "For CHART: {column_name: x|y|series} using exact result columns",
                                            },
                                            "counter_column": {
                                                "type": "string",
                                                "description": "For COUNTER: numeric column to display",
                                            },
                                            "counter_label": {"type": "string"},
                                            "options": {"type": "object", "description": "Raw options override"},
                                        },
                                        "required": ["type", "name"],
                                    },
                                },
                            },
                            "required": ["name", "data_source_id", "query"],
                        },
                    },
                    "derived": {
                        "type": "array",
                        "description": (
                            "Second-phase queries on the Query Results source. Query text may use "
                            "{{cached_query.KEY}} placeholders; SQLite SQL syntax."
                        ),
                        "items": {
                            "type": "object",
                            "properties": {
                                "key": {"type": "string"},
                                "name": {"type": "string"},
                                "description": {"type": "string"},
                                "query": {"type": "string"},
                                "visualizations": {"type": "array", "items": {"type": "object"}},
                            },
                            "required": ["name", "query"],
                        },
                    },
                    "widgets": {
                        "type": "array",
                        "description": "Ordered widget list; auto-laid-out unless position given",
                        "items": {
                            "type": "object",
                            "properties": {
                                "visualization": {
                                    "type": "string",
                                    "description": "Visualization name from the queries/derived specs",
                                },
                                "text": {"type": "string", "description": "Markdown for text-box widgets"},
                                "role": {
                                    "type": "string",
                                    "description": "Layout role: title, section, kpi, half, third, full",
                                },
                                "position": {
                                    "type": "object",
                                    "description": "Explicit {col,row,sizeX,sizeY} to override auto-layout",
                                },
                            },
                        },
                    },
                    "publish": {"type": "boolean", "default": True},
                },
                "required": ["name", "queries", "widgets"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "refresh_queries_and_wait",
            "description": (
                "Refresh saved queries and wait until their cached results are stored. Required before "
                "creating queries on the Query Results data source that read cached_query_{id} tables."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "query_ids": {"type": "array", "items": {"type": "integer"}},
                    "timeout_seconds": {"type": "integer", "default": 180},
                },
                "required": ["query_ids"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "create_multi_visualization_query",
            "description": (
                "Create one query plus several visualizations in a single call (e.g. a wide summary row "
                "rendered as multiple KPI counters). Query text is validated by execution first; column "
                "names in visualization specs are checked against real result columns. The query is "
                "published (is_draft=false) on success."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "name": {"type": "string"},
                    "query": {"type": "string"},
                    "data_source_id": {"type": "integer"},
                    "description": {"type": "string"},
                    "visualizations": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "type": {"type": "string"},
                                "name": {"type": "string"},
                                "chart_type": {"type": "string"},
                                "column_mapping": {"type": "object"},
                                "counter_column": {"type": "string"},
                                "counter_label": {"type": "string"},
                                "options": {"type": "object"},
                            },
                            "required": ["type", "name"],
                        },
                    },
                },
                "required": ["name", "query", "data_source_id", "visualizations"],
            },
        },
    },
    # --- Alerts ---
    {
        "type": "function",
        "function": {
            "name": "get_alert_template_guide",
            "description": (
                "Mustache variables and end-to-end workflow for alert notification templates "
                "(custom_subject / custom_body). Call before writing webhook or Discord custom payloads."
            ),
            "parameters": {"type": "object", "properties": {}},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "list_alerts",
            "description": "List all alerts with their state and linked queries.",
            "parameters": {"type": "object", "properties": {}},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_alert",
            "description": "Get one alert's configuration, templates, state, and subscriptions context.",
            "parameters": {
                "type": "object",
                "properties": {"alert_id": {"type": "integer"}},
                "required": ["alert_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "create_alert",
            "description": (
                "Create an alert on a query and optionally subscribe destinations. "
                "op: >, >=, <, <=, ==, !=. selector: first|min|max. "
                "custom_subject/custom_body: Mustache templates (see get_alert_template_guide). "
                "destination_ids: subscribe after creation. Validates column against query results by default."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "name": {"type": "string"},
                    "query_id": {"type": "integer"},
                    "column": {"type": "string"},
                    "op": {"type": "string"},
                    "value": {},
                    "rearm": {"type": "integer"},
                    "tags": {"type": "array", "items": {"type": "string"}},
                    "selector": {"type": "string", "enum": ["first", "min", "max"], "default": "first"},
                    "custom_subject": {"type": "string"},
                    "custom_body": {"type": "string"},
                    "send_for_each_row": {"type": "boolean", "default": False},
                    "destination_ids": {"type": "array", "items": {"type": "integer"}},
                    "validate_column": {"type": "boolean", "default": True},
                },
                "required": ["name", "query_id", "column", "op", "value"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "update_alert",
            "description": "Update an alert (options may include custom_body, custom_subject, send_for_each_row).",
            "parameters": {
                "type": "object",
                "properties": {
                    "alert_id": {"type": "integer"},
                    "name": {"type": "string"},
                    "query_id": {"type": "integer"},
                    "options": {"type": "object"},
                    "rearm": {"type": "integer"},
                    "tags": {"type": "array", "items": {"type": "string"}},
                },
                "required": ["alert_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "delete_alert",
            "description": "Permanently delete an alert.",
            "parameters": {
                "type": "object",
                "properties": {"alert_id": {"type": "integer"}},
                "required": ["alert_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "evaluate_alert",
            "description": "Manually evaluate an alert and send notifications if it triggers.",
            "parameters": {
                "type": "object",
                "properties": {"alert_id": {"type": "integer"}},
                "required": ["alert_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "list_alert_subscriptions",
            "description": "List destinations subscribed to an alert.",
            "parameters": {
                "type": "object",
                "properties": {"alert_id": {"type": "integer"}},
                "required": ["alert_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "subscribe_alert",
            "description": "Subscribe a notification destination to an alert.",
            "parameters": {
                "type": "object",
                "properties": {
                    "alert_id": {"type": "integer"},
                    "destination_id": {"type": "integer"},
                },
                "required": ["alert_id", "destination_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "unsubscribe_alert",
            "description": "Remove a destination subscription from an alert.",
            "parameters": {
                "type": "object",
                "properties": {
                    "alert_id": {"type": "integer"},
                    "subscription_id": {"type": "integer"},
                },
                "required": ["alert_id", "subscription_id"],
            },
        },
    },
    # --- Destinations ---
    {
        "type": "function",
        "function": {
            "name": "list_destinations",
            "description": "List notification destinations (Slack, email, webhooks, etc.).",
            "parameters": {"type": "object", "properties": {}},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_destination",
            "description": "Get one notification destination (type, options, tags).",
            "parameters": {
                "type": "object",
                "properties": {"destination_id": {"type": "integer"}},
                "required": ["destination_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "list_destination_types",
            "description": (
                "List destination types with config schemas and template summaries. "
                "Call get_destination_type for webhook/Discord template examples."
            ),
            "parameters": {
                "type": "object",
                "properties": {"q": {"type": "string", "description": "Optional filter"}},
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_destination_type",
            "description": (
                "Full docs for a destination type: required options, template location (alert vs destination), "
                "and example custom_body/custom_subject or Teams message_template."
            ),
            "parameters": {
                "type": "object",
                "properties": {"type": {"type": "string", "description": "e.g. webhook, discord_webhook, slack"}},
                "required": ["type"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "create_destination",
            "description": (
                "Create a notification destination. Call get_destination_type first for required options "
                "and webhook template examples."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "name": {"type": "string"},
                    "type": {"type": "string"},
                    "options": {"type": "object"},
                    "tags": {"type": "array", "items": {"type": "string"}},
                },
                "required": ["name", "type", "options"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "update_destination",
            "description": "Update a notification destination.",
            "parameters": {
                "type": "object",
                "properties": {
                    "destination_id": {"type": "integer"},
                    "name": {"type": "string"},
                    "type": {"type": "string"},
                    "options": {"type": "object"},
                    "tags": {"type": "array", "items": {"type": "string"}},
                },
                "required": ["destination_id"],
            },
        },
    },
    # --- ML models (Rewatch extension) ---
    {
        "type": "function",
        "function": {
            "name": "list_ml_models",
            "description": "List or search ML models with training state.",
            "parameters": {
                "type": "object",
                "properties": {
                    "q": {"type": "string"},
                    "page_size": {"type": "integer", "default": 10},
                },
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_ml_model",
            "description": "Get an ML model: configuration, linked query, training state.",
            "parameters": {
                "type": "object",
                "properties": {"model_id": {"type": "integer"}},
                "required": ["model_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "create_ml_model",
            "description": (
                "Create an ML model bound to a query. options must include regressor, features, and targets."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "name": {"type": "string"},
                    "query_id": {"type": "integer"},
                    "options": {"type": "object"},
                    "description": {"type": "string"},
                    "tags": {"type": "array", "items": {"type": "string"}},
                },
                "required": ["name", "query_id", "options"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "update_ml_model",
            "description": "Update an ML model definition.",
            "parameters": {
                "type": "object",
                "properties": {
                    "model_id": {"type": "integer"},
                    "name": {"type": "string"},
                    "description": {"type": "string"},
                    "options": {"type": "object"},
                    "tags": {"type": "array", "items": {"type": "string"}},
                },
                "required": ["model_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "train_ml_model",
            "description": "Start training for an ML model (asynchronous).",
            "parameters": {
                "type": "object",
                "properties": {"model_id": {"type": "integer"}},
                "required": ["model_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "predict_ml_model",
            "description": "Start a prediction run for a trained ML model (asynchronous).",
            "parameters": {
                "type": "object",
                "properties": {
                    "model_id": {"type": "integer"},
                    "body": {"type": "object", "description": "Optional prediction parameters"},
                },
                "required": ["model_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_predictions",
            "description": "List prediction results, optionally for one ML model.",
            "parameters": {
                "type": "object",
                "properties": {
                    "model_id": {"type": "integer"},
                    "page_size": {"type": "integer", "default": 10},
                },
            },
        },
    },
    # --- Indexers (Rewatch extension) ---
    {
        "type": "function",
        "function": {
            "name": "list_indexers",
            "description": "List indexers (ingestion jobs that materialize query results).",
            "parameters": {"type": "object", "properties": {}},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_indexer",
            "description": "Get one indexer by id.",
            "parameters": {
                "type": "object",
                "properties": {"indexer_id": {"type": "integer"}},
                "required": ["indexer_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "create_indexer",
            "description": "Create an indexer that runs a query and writes to a target data source.",
            "parameters": {
                "type": "object",
                "properties": {
                    "name": {"type": "string"},
                    "query_id": {"type": "integer"},
                    "data_source_id": {"type": "integer"},
                    "options": {"type": "object"},
                    "tags": {"type": "array", "items": {"type": "string"}},
                },
                "required": ["name", "query_id", "data_source_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "update_indexer",
            "description": "Update an indexer definition.",
            "parameters": {
                "type": "object",
                "properties": {
                    "indexer_id": {"type": "integer"},
                    "name": {"type": "string"},
                    "query_id": {"type": "integer"},
                    "data_source_id": {"type": "integer"},
                    "options": {"type": "object"},
                    "tags": {"type": "array", "items": {"type": "string"}},
                },
                "required": ["indexer_id"],
            },
        },
    },
    # --- API meta (full REST coverage) ---
    {
        "type": "function",
        "function": {
            "name": "list_endpoints",
            "description": (
                "Browse all Rewatch REST API endpoints from the live OpenAPI spec. "
                "Filter by tag (Queries, Dashboards, Alerts, ...) or free-text search. "
                "Use describe_endpoint for parameters and call_api to invoke."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "tag": {"type": "string", "description": "Filter by OpenAPI tag"},
                    "search": {"type": "string", "description": "Search path or summary text"},
                },
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "describe_endpoint",
            "description": (
                "Get full OpenAPI details for one endpoint: parameters, request body, responses. "
                "Path must use template form, e.g. /api/queries/{query_id}."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "method": {"type": "string", "description": "HTTP method, e.g. GET or POST"},
                    "path": {"type": "string", "description": "OpenAPI path template"},
                },
                "required": ["method", "path"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "call_api",
            "description": (
                "Invoke any Rewatch REST API endpoint and return JSON. "
                "Path must use real IDs (not {placeholders}). "
                "Prefer dedicated tools when they cover the task."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "method": {"type": "string"},
                    "path": {"type": "string", "description": "Concrete path, e.g. /api/queries/42"},
                    "query_params": {"type": "object", "description": "URL query parameters"},
                    "body": {"type": "object", "description": "JSON request body for POST/PUT/DELETE"},
                },
                "required": ["method", "path"],
            },
        },
    },
    # --- Dashboard examples ---
    {
        "type": "function",
        "function": {
            "name": "list_dashboard_examples",
            "description": (
                "List curated build_dashboard_from_spec examples (DeFi, weather, airport, SQL KPIs, viz gallery). "
                "Use before building complex dashboards."
            ),
            "parameters": {
                "type": "object",
                "properties": {"q": {"type": "string", "description": "Optional search filter"}},
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_dashboard_example",
            "description": "Get a full spec snippet for one dashboard example by id.",
            "parameters": {
                "type": "object",
                "properties": {
                    "id": {
                        "type": "string",
                        "description": "Example id, e.g. ethereum_defi, montpellier_weather, viz_demo",
                    }
                },
                "required": ["id"],
            },
        },
    },
    # --- Production instance patterns ---
    {
        "type": "function",
        "function": {
            "name": "list_instance_examples",
            "description": (
                "List real-world query and visualization patterns from a production Rewatch "
                "deployment (derived SQL, Python chaining, EVM logs/state, GraphQL subgraphs, "
                "KPI counters, dashboard layouts). Use before building analytics dashboards."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "q": {"type": "string", "description": "Optional search filter"},
                    "category": {
                        "type": "string",
                        "description": (
                            "Optional category: query_results, python, evmlogs, evmstate, "
                            "graphql, pg, dashboard, visualization, coingecko, dune"
                        ),
                    },
                },
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_instance_example",
            "description": (
                "Get query text, visualization mappings, and layout snippets for one production "
                "instance pattern by id (e.g. results_derived_cte, python_get_query_result, "
                "dola_health_dashboard_layout, counter_wide_row)."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "id": {
                        "type": "string",
                        "description": "Instance example id",
                    }
                },
                "required": ["id"],
            },
        },
    },
    # --- Web ---
    {
        "type": "function",
        "function": {
            "name": "discover_public_sources",
            "description": (
                "Find public APIs, open datasets, and JSON/CSV endpoints for a topic on the internet. "
                "Runs multiple targeted searches, ranks results, and extracts candidate API URLs. "
                "Use this first when the user wants a new query/report from an external public source "
                "that is not already in list_data_sources."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "topic": {
                        "type": "string",
                        "description": "Subject to research (e.g. 'SNCF train delays', 'US weather alerts')",
                    },
                    "data_kind": {
                        "type": "string",
                        "enum": ["json", "csv", "api", "dataset", "openapi"],
                        "default": "json",
                        "description": "Preferred public data format",
                    },
                    "max_results": {"type": "integer", "default": 8},
                },
                "required": ["topic"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "web_search",
            "description": (
                "Search the public internet for documentation, APIs, datasets, SQL syntax, libraries, "
                "or current information. Prefer discover_public_sources when starting from an unknown topic."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "q": {"type": "string", "description": "Search query"},
                    "max_results": {"type": "integer", "default": 5},
                    "search_type": {
                        "type": "string",
                        "enum": ["general", "api", "dataset", "docs", "openapi"],
                        "default": "general",
                        "description": "Bias results toward APIs, datasets, docs, or OpenAPI specs",
                    },
                    "site": {
                        "type": "string",
                        "description": "Optional domain to restrict search (e.g. github.com or data.gouv.fr)",
                    },
                },
                "required": ["q"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "fetch_url",
            "description": (
                "Fetch a public web page or JSON endpoint. Auto-detects JSON and OpenAPI specs, "
                "extracts candidate API URLs from HTML docs, and returns a readable preview."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "url": {"type": "string", "description": "http or https URL"},
                    "mode": {
                        "type": "string",
                        "enum": ["auto", "text", "json"],
                        "default": "auto",
                        "description": "auto detects JSON; json requires valid JSON response",
                    },
                },
                "required": ["url"],
            },
        },
    },
    # --- Docs ---
    {
        "type": "function",
        "function": {
            "name": "search_docs",
            "description": "Search Rewatch help documentation topics by keyword.",
            "parameters": {
                "type": "object",
                "properties": {"q": {"type": "string"}},
                "required": ["q"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_docs_topic",
            "description": "Get details and URL for a help topic (getting_started, queries, dashboards, alerts, etc.).",
            "parameters": {
                "type": "object",
                "properties": {"topic_id": {"type": "string"}},
                "required": ["topic_id"],
            },
        },
    },
]


class ToolContext:
    def __init__(self, *, base_url: str, api_key: str, help_base_url: str):
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.help_base_url = help_base_url
        self._session = requests.Session()
        self._session.headers.update({"Authorization": f"Key {api_key}"})

    def request(self, method: str, path: str, *, params: Optional[dict] = None, body: Optional[dict] = None) -> Any:
        if not path.startswith("/"):
            path = "/" + path
        resp = self._session.request(method.upper(), f"{self.base_url}{path}", params=params, json=body, timeout=120)
        if resp.status_code >= 400:
            raise RuntimeError(f"{method.upper()} {path} failed ({resp.status_code}): {resp.text[:1500]}")
        if not resp.content:
            return {"status_code": resp.status_code}
        return resp.json()

    def poll_job(self, job: dict, timeout_seconds: int = 120) -> int:
        deadline = time.monotonic() + timeout_seconds
        job = _as_dict(job, "job payload")
        job_id = job["id"]
        while time.monotonic() < deadline:
            status = job.get("status")
            if status == JOB_FINISHED:
                result_id = job.get("query_result_id") or job.get("result")
                if not result_id:
                    raise RuntimeError(f"Job {job_id} finished without a result id")
                return result_id
            if status in (JOB_FAILED, JOB_CANCELED):
                raise RuntimeError(job.get("error") or "Query execution failed")
            time.sleep(1)
            resp = self.request("GET", f"/api/jobs/{job_id}")
            next_job = resp.get("job") if isinstance(resp, dict) else resp
            job = _as_dict(next_job, "job status")
        raise RuntimeError(f"Query timed out (job {job_id})")

    def run_query_tool(self, args: dict) -> dict:
        query_id = args.get("query_id")
        max_rows = args.get("max_rows", 100)
        max_age = args.get("max_age", -1)
        if query_id is not None:
            body = {"max_age": max_age}
            if args.get("parameters"):
                body["parameters"] = args["parameters"]
            response = self.request("POST", f"/api/queries/{query_id}/results", body=body)
        elif args.get("query_text") and args.get("data_source_id"):
            body = {
                "query": args["query_text"],
                "data_source_id": args["data_source_id"],
                "max_age": max_age,
                "parameters": args.get("parameters") or {},
                "apply_auto_limit": True,
            }
            response = self.request("POST", "/api/query_results", body=body)
        else:
            raise RuntimeError("Provide query_id or query_text + data_source_id")

        if "job" in response:
            result_id = self.poll_job(_as_dict(response["job"], "async job"))
            if query_id is not None:
                response = self.request("GET", f"/api/queries/{query_id}/results/{result_id}.json")
            else:
                response = self.request("GET", f"/api/query_results/{result_id}")

        columns, rows = _extract_query_result_rows(response)
        max_rows = args.get("max_rows", 100)
        query_result = response.get("query_result") if isinstance(response, dict) else {}
        query_result_id = query_result.get("id") if isinstance(query_result, dict) else None
        result = {
            "query_result_id": query_result_id,
            "columns": columns,
            "row_count": len(rows),
            "rows": rows[:max_rows],
            "visualization_hints": build_visualization_hints(columns, rows),
            "note": f"Showing first {max_rows} rows" if len(rows) > max_rows else None,
        }
        return result

    def _execute_saved_query_validation(self, query_id: int, parameters: Optional[dict] = None) -> dict[str, Any]:
        try:
            result = self.run_query_tool(
                {
                    "query_id": query_id,
                    "max_age": 0,
                    "max_rows": 10,
                    "parameters": parameters or {},
                }
            )
            return {
                "status": "ok",
                "message": f"Query ran successfully ({result.get('row_count', 0)} rows returned).",
                **result,
            }
        except RuntimeError as exc:
            message = str(exc)
            if "Missing parameter" in message:
                return {
                    "status": "needs_parameters",
                    "message": message,
                }
            return {
                "status": "error",
                "message": message,
            }

    def _test_sql_before_save(self, sql: str, data_source_id: int, parameters: Optional[dict] = None) -> dict[str, Any]:
        try:
            result = self.run_query_tool(
                {
                    "query_text": sql,
                    "data_source_id": data_source_id,
                    "max_age": 0,
                    "max_rows": 10,
                    "parameters": parameters or {},
                }
            )
            return {
                "status": "ok",
                "phase": "pre_save",
                "message": f"SQL test passed ({result.get('row_count', 0)} rows returned).",
                **result,
            }
        except RuntimeError as exc:
            message = str(exc)
            if "Missing parameter" in message:
                return {
                    "status": "needs_parameters",
                    "phase": "pre_save",
                    "message": message,
                }
            return {
                "status": "error",
                "phase": "pre_save",
                "message": message,
            }

    def _validate_saved_query(self, query: dict[str, Any]) -> dict[str, Any]:
        query = _as_dict(query, "saved query")
        query_id = query.get("id")
        if not query_id:
            return query
        query["validation"] = self._execute_saved_query_validation(query_id)
        return query

    def create_query_tool(self, args: dict) -> Any:
        pre_validation = self._test_sql_before_save(args["query"], args["data_source_id"])
        if pre_validation.get("status") == "error":
            raise RuntimeError(f"Query failed validation before save: {pre_validation['message']}")

        query = _as_dict(self.request("POST", "/api/queries", body=_merge_body(**args)), "create query")
        query = self._validate_saved_query(query)
        post_save = query.get("validation")
        if not isinstance(post_save, dict):
            post_save = {}
        query["validation"] = {
            "pre_save": pre_validation,
            "post_save": post_save,
        }
        if post_save.get("status") == "error":
            query["validation"]["action_required"] = (
                f"Query #{query.get('id')} was saved but failed to run. Fix the SQL with update_query."
            )
        return query

    def update_query_tool(self, args: dict) -> Any:
        args = dict(args)
        query_id = args.pop("query_id")
        current = _as_dict(self.request("GET", f"/api/queries/{query_id}"), "query")
        pre_validation = None
        if "query" in args:
            data_source_id = args.get("data_source_id") or current.get("data_source_id")
            pre_validation = self._test_sql_before_save(args["query"], data_source_id)
            if pre_validation.get("status") == "error":
                raise RuntimeError(f"Query failed validation before save: {pre_validation['message']}")

        body = _merge_body(**args)
        body.setdefault("version", current.get("version"))
        query = _as_dict(self.request("POST", f"/api/queries/{query_id}", body=body), "update query")
        post_validation = self._execute_saved_query_validation(query_id)
        validation: dict[str, Any] = {"post_save": post_validation}
        if pre_validation is not None:
            validation["pre_save"] = pre_validation
        query["validation"] = validation
        if post_validation.get("status") == "error":
            query["validation"]["action_required"] = (
                f"Query #{query_id} was updated but failed to run. Fix the SQL with update_query."
            )
        return query

    def update_dashboard_tool(self, args: dict) -> Any:
        args = dict(args)
        dashboard_id = args.pop("dashboard_id")
        current = self.request("GET", f"/api/dashboards/{dashboard_id}")
        body = _merge_body(**args)
        body.setdefault("version", current.get("version"))
        return self.request("POST", f"/api/dashboards/{dashboard_id}", body=body)

    def update_ml_model_tool(self, args: dict) -> Any:
        args = dict(args)
        model_id = args.pop("model_id")
        current = self.request("GET", f"/api/ml_models/{model_id}")
        body = _merge_body(**args)
        body.setdefault("version", current.get("version"))
        return self.request("POST", f"/api/ml_models/{model_id}", body=body)

    def create_alert_tool(self, args: dict) -> Any:
        args = dict(args)
        column = args["column"]
        column_check: dict[str, Any] = {}
        if args.get("validate_column", True):
            query_validation = self._execute_saved_query_validation(args["query_id"])
            if query_validation.get("status") == "needs_parameters":
                raise RuntimeError(
                    "Cannot create alert: the linked query requires parameter values. "
                    "Run the query with parameters first or set defaults on the query."
                )
            if query_validation.get("status") == "error":
                raise RuntimeError(
                    "Cannot create alert because the query failed to run: "
                    f"{query_validation['message']}"
                )
            column_check = alert_catalog.validate_alert_column(column, query_validation.get("columns") or [])
            if not column_check.get("valid"):
                raise RuntimeError(
                    f"{column_check.get('message')} Available columns: {column_check.get('available_columns')}"
                )
            column = column_check.get("column", column)

        try:
            options = alert_catalog.build_alert_options(
                column=column,
                op=args["op"],
                value=args["value"],
                selector=args.get("selector", "first"),
                custom_subject=args.get("custom_subject"),
                custom_body=args.get("custom_body"),
                send_for_each_row=bool(args.get("send_for_each_row")),
            )
        except ValueError as exc:
            raise RuntimeError(str(exc)) from exc
        body = _merge_body(
            name=args["name"],
            query_id=args["query_id"],
            options=options,
            rearm=args.get("rearm"),
            tags=args.get("tags"),
        )
        alert = self.request("POST", "/api/alerts", body=body)
        result: dict[str, Any] = {"alert": alert}
        if column_check:
            result["column_validation"] = column_check
        destination_ids = args.get("destination_ids") or []
        if destination_ids:
            subscriptions = []
            for destination_id in destination_ids:
                subscriptions.append(
                    self.request(
                        "POST",
                        f"/api/alerts/{alert['id']}/subscriptions",
                        body={"destination_id": destination_id},
                    )
                )
            result["subscriptions"] = subscriptions
        return result

    def list_destination_types_tool(self, args: dict) -> Any:
        api_types = self.request("GET", "/api/destinations/types")
        return alert_catalog.list_destination_types_catalog(api_types, query=args.get("q"))

    def get_destination_type_tool(self, args: dict) -> Any:
        dest_type = args["type"]
        api_entry = None
        for entry in self.request("GET", "/api/destinations/types"):
            if entry.get("type") == dest_type:
                api_entry = entry
                break
        return _require_catalog_result(
            alert_catalog.get_destination_type(dest_type, api_entry),
            "Destination type",
        )

    def get_query_tool(self, args: dict) -> Any:
        query = _as_dict(self.request("GET", f"/api/queries/{args['query_id']}"), "query")
        query = self._validate_saved_query(query)
        validation = query.get("validation") or {}
        if validation.get("status") == "ok":
            columns = validation.get("columns") or []
            rows = validation.get("rows") or []
            query["visualization_hints"] = validation.get("visualization_hints") or build_visualization_hints(
                columns, rows
            )
            visualizations = query.get("visualizations")
            if isinstance(visualizations, list):
                query["visualizations"] = enrich_visualizations_for_assistant(visualizations, columns, rows)
            unhealthy = [
                viz
                for viz in (query.get("visualizations") or [])
                if isinstance(viz, dict) and not (viz.get("options_health") or {}).get("is_healthy", True)
            ]
            if unhealthy:
                query["visualization_action_required"] = {
                    "action": "fix_query_visualizations",
                    "query_id": query.get("id"),
                    "broken_visualization_ids": [viz.get("id") for viz in unhealthy if viz.get("id")],
                    "message": (
                        f"{len(unhealthy)} visualization(s) reference columns not in query results. "
                        "Call fix_query_visualizations to auto-correct mappings."
                    ),
                }
        return query

    def get_visualization_tool(self, args: dict) -> Any:
        visualization = _as_dict(
            self.request("GET", f"/api/visualizations/{args['visualization_id']}"),
            "visualization",
        )
        query_id = visualization.get("query_id")
        if not query_id:
            return visualization

        query_validation = self._execute_saved_query_validation(query_id)
        visualization["query_validation"] = query_validation
        if query_validation.get("status") != "ok":
            return visualization

        columns = query_validation.get("columns") or []
        rows = query_validation.get("rows") or []
        enriched = enrich_visualizations_for_assistant([visualization], columns, rows)
        if enriched:
            visualization = enriched[0]
        visualization["visualization_hints"] = query_validation.get("visualization_hints") or build_visualization_hints(
            columns, rows
        )
        return visualization

    def fix_query_visualizations_tool(self, args: dict) -> dict[str, Any]:
        query_id = args["query_id"]
        query = _as_dict(self.request("GET", f"/api/queries/{query_id}"), "query")
        query_validation = self._execute_saved_query_validation(query_id)
        if query_validation.get("status") == "needs_parameters":
            raise RuntimeError(
                "Cannot fix visualizations: the linked query requires parameter values. "
                "Run the query with parameters first or set defaults on the query."
            )
        if query_validation.get("status") == "error":
            raise RuntimeError(
                "Cannot fix visualizations because the query failed to run: "
                f"{query_validation['message']}"
            )

        columns = query_validation.get("columns") or []
        rows = query_validation.get("rows") or []
        visualizations = query.get("visualizations") if isinstance(query.get("visualizations"), list) else []
        fixed: list[dict[str, Any]] = []
        skipped: list[dict[str, Any]] = []

        for visualization in visualizations:
            if not isinstance(visualization, dict):
                continue
            viz_id = visualization.get("id")
            viz_type = (visualization.get("type") or "").upper()
            if not viz_id or viz_type in {"TABLE", "DETAILS"}:
                skipped.append({"id": viz_id, "name": visualization.get("name"), "reason": "no column mapping"})
                continue

            current_options = visualization.get("options") if isinstance(visualization.get("options"), dict) else {}
            options, corrections = normalize_visualization_options(viz_type, current_options, columns, rows)
            updated = _as_dict(
                self.request(
                    "POST",
                    f"/api/visualizations/{viz_id}",
                    body={"name": visualization.get("name"), "options": options},
                ),
                "visualization",
            )
            entry = {
                "id": viz_id,
                "name": updated.get("name") or visualization.get("name"),
                "type": viz_type,
                "resolved_options": options,
            }
            if corrections:
                entry["column_corrections"] = corrections
            fixed.append(entry)

        return {
            "query_id": query_id,
            "query_validation": query_validation,
            "fixed_count": len(fixed),
            "skipped_count": len(skipped),
            "fixed": fixed,
            "skipped": skipped,
        }

    def create_visualization_tool(self, args: dict) -> Any:
        query_validation = self._execute_saved_query_validation(args["query_id"])
        if query_validation.get("status") == "needs_parameters":
            raise RuntimeError(
                "Cannot create visualization: the linked query requires parameter values. "
                "Run the query with parameters first or set defaults on the query."
            )
        if query_validation.get("status") == "error":
            raise RuntimeError(
                "Cannot create visualization because the query failed to run: "
                f"{query_validation['message']}"
            )

        viz_type = (args.get("type") or "").upper()
        columns = query_validation.get("columns") or []
        rows = query_validation.get("rows") or []

        user_options = args.get("options")
        if not user_options:
            options, corrections = normalize_visualization_options(
                viz_type,
                suggest_visualization_options(viz_type, columns, rows),
                columns,
                rows,
            )
        else:
            options, corrections = normalize_visualization_options(viz_type, user_options, columns, rows)

        body = _merge_body(
            query_id=args["query_id"],
            type=args["type"],
            name=args["name"],
            options=options or {},
            description=args.get("description"),
        )
        visualization = _as_dict(self.request("POST", "/api/visualizations", body=body), "visualization")
        visualization["query_validation"] = query_validation
        visualization["resolved_options"] = options
        if corrections:
            visualization["column_corrections"] = corrections
        if not user_options:
            visualization["auto_suggested_options"] = options
        return visualization

    def update_visualization_tool(self, args: dict) -> Any:
        args = dict(args)
        visualization_id = args.pop("visualization_id")
        remap_columns = args.pop("remap_columns", True)
        current = _as_dict(self.request("GET", f"/api/visualizations/{visualization_id}"), "visualization")
        query_id = current.get("query_id")
        corrections: list[str] = []
        query_validation: Optional[dict[str, Any]] = None

        should_remap = remap_columns and query_id
        if should_remap or "options" in args:
            if not query_id:
                raise RuntimeError("Cannot validate visualization options without a parent query_id.")
            query_validation = self._execute_saved_query_validation(query_id)
            if query_validation.get("status") == "needs_parameters":
                raise RuntimeError(
                    "Cannot update visualization options: the linked query requires parameter values. "
                    "Run the query with parameters first or set defaults on the query."
                )
            if query_validation.get("status") == "error":
                raise RuntimeError(
                    "Cannot update visualization options because the query failed to run: "
                    f"{query_validation['message']}"
                )
            viz_type = (args.get("type") or current.get("type") or "").upper()
            current_options = current.get("options") if isinstance(current.get("options"), dict) else {}
            merged_options = {**current_options, **(args.get("options") or {})}
            options, corrections = normalize_visualization_options(
                viz_type,
                merged_options,
                query_validation.get("columns") or [],
                query_validation.get("rows") or [],
            )
            args["options"] = options

        result = self.request("POST", f"/api/visualizations/{visualization_id}", body=_merge_body(**args))
        if isinstance(result, dict):
            if corrections:
                result["column_corrections"] = corrections
            if query_validation:
                result["query_validation"] = query_validation
        return result

    def get_dashboard_tool(self, args: dict) -> Any:
        dashboard = _as_dict(
            self.request("GET", f"/api/dashboards/{args['dashboard_id']}"),
            "dashboard",
        )
        return enrich_dashboard_for_assistant(dashboard)

    def add_widget_tool(self, args: dict) -> Any:
        _require_widget_content(args.get("visualization_id"), args.get("text"))
        dashboard_id = args["dashboard_id"]
        raw_options = args.get("options")
        viz_type = None
        if args.get("visualization_id"):
            try:
                viz = _as_dict(
                    self.request("GET", f"/api/visualizations/{args['visualization_id']}"),
                    "visualization",
                )
                viz_type = viz.get("type")
            except RuntimeError:
                viz_type = None
        if has_explicit_position(raw_options):
            options = normalize_widget_options(raw_options, visualization_type=viz_type)
        else:
            dashboard = _as_dict(self.request("GET", f"/api/dashboards/{dashboard_id}"), "dashboard")
            widgets = dashboard.get("widgets") if isinstance(dashboard.get("widgets"), list) else []
            options = prepare_widget_options(
                widgets,
                visualization_type=viz_type,
                text=args.get("text"),
                options=raw_options,
            )

        body = _merge_body(
            dashboard_id=dashboard_id,
            visualization_id=args.get("visualization_id"),
            text=args.get("text"),
            options=options,
            width=args.get("width", 1),
        )
        widget = _as_dict(self.request("POST", "/api/widgets", body=body), "widget")
        dashboard = _as_dict(self.request("GET", f"/api/dashboards/{dashboard_id}"), "dashboard")
        widgets = dashboard.get("widgets") if isinstance(dashboard.get("widgets"), list) else []
        widget["layout_summary"] = summarize_dashboard_layout(widgets)
        return widget

    def update_widget_tool(self, args: dict) -> Any:
        args = dict(args)
        widget_id = args.pop("widget_id")
        body: dict[str, Any] = {}
        if "text" in args:
            body["text"] = args.pop("text")
        if "options" in args:
            widget = _as_dict(self.request("GET", f"/api/widgets/{widget_id}"), "widget")
            dashboard_id = widget.get("dashboard_id")
            viz = widget.get("visualization") if isinstance(widget.get("visualization"), dict) else {}
            dashboard = _as_dict(self.request("GET", f"/api/dashboards/{dashboard_id}"), "dashboard")
            widgets = dashboard.get("widgets") if isinstance(dashboard.get("widgets"), list) else []
            body["options"] = prepare_widget_options_for_update(
                widget,
                widgets,
                visualization_type=viz.get("type"),
                text=body.get("text", widget.get("text")),
                options=args.pop("options"),
            )
        if not body:
            raise RuntimeError("Provide text and/or options to update a widget.")
        return self.request("POST", f"/api/widgets/{widget_id}", body=body)

    def build_dashboard_from_spec_tool(self, args: dict) -> Any:
        try:
            return dashboard_builder.build_dashboard_from_spec(
                self.request,
                name=args["name"],
                queries=args["queries"],
                widgets=args["widgets"],
                derived=args.get("derived"),
                publish=args.get("publish", True),
            )
        except dashboard_builder.DashboardBuildError as exc:
            raise RuntimeError(str(exc)) from exc

    def refresh_queries_and_wait_tool(self, args: dict) -> Any:
        return dashboard_builder.refresh_queries_and_wait(
            self.request,
            args["query_ids"],
            timeout_seconds=args.get("timeout_seconds", 180),
        )

    def create_multi_visualization_query_tool(self, args: dict) -> Any:
        try:
            return dashboard_builder.create_query_with_visualizations(
                self.request,
                name=args["name"],
                query=args["query"],
                data_source_id=args["data_source_id"],
                visualizations=args["visualizations"],
                description=args.get("description"),
            )
        except dashboard_builder.DashboardBuildError as exc:
            raise RuntimeError(str(exc)) from exc


# Keep tool results within a sane share of the model context. Oversized
# payloads get structurally truncated while preserving ids, columns, and validation.
_PRESERVE_KEYS = frozenset(
    {
        "columns",
        "validation",
        "query_validation",
        "visualization_hints",
        "options_health",
        "visualization_action_required",
        "column_corrections",
        "auto_suggested_options",
        "error",
        "app_link",
        "preview_image_url",
        "candidate_endpoints",
        "candidate_api_urls",
        "discovered_urls",
        "json_preview",
        "recommended_workflow",
        "assistant_note",
        "effective_query",
        "name",
        "id",
        "query_id",
        "dashboard_id",
        "visualization_id",
        "alert_id",
        "destination_id",
        "model_id",
        "widget_id",
        "row_count",
        "count",
        "status",
        "message",
        "layout_summary",
        "spec_snippet",
        "patterns",
        "examples",
        "known_ids",
    }
)
_TRUNCATION_LIST_KEEP = 40
_TRUNCATION_ROW_KEEP = 15
_TRUNCATION_SCHEMA_TABLE_KEEP = 80


def _max_tool_result_chars() -> int:
    return assistant_max_tool_result_chars()


def _shrink_rows(rows: list[Any]) -> list[Any]:
    if len(rows) <= _TRUNCATION_ROW_KEEP:
        return [_shrink_payload(item, depth=1) for item in rows]
    kept = [_shrink_payload(item, depth=1) for item in rows[:_TRUNCATION_ROW_KEEP]]
    kept.append(f"... truncated {len(rows) - _TRUNCATION_ROW_KEEP} more rows ...")
    return kept


def _shrink_schema(value: Any) -> Any:
    if not isinstance(value, dict):
        return _shrink_payload(value, depth=0)
    tables = value.get("schema") or value.get("tables")
    if isinstance(tables, list):
        trimmed_tables = []
        for table in tables[:_TRUNCATION_SCHEMA_TABLE_KEEP]:
            if not isinstance(table, dict):
                trimmed_tables.append(table)
                continue
            columns = table.get("columns") or []
            col_names = []
            for column in columns:
                if isinstance(column, dict) and column.get("name"):
                    col_names.append(column["name"])
                elif isinstance(column, str):
                    col_names.append(column)
            trimmed_tables.append(
                {
                    **{k: v for k, v in table.items() if k != "columns"},
                    "columns": col_names[:200],
                    **(
                        {"column_count": len(columns), "columns_truncated": len(columns) > 200}
                        if len(columns) > 200
                        else {}
                    ),
                }
            )
        out = dict(value)
        key = "schema" if "schema" in value else "tables"
        out[key] = trimmed_tables
        if len(tables) > _TRUNCATION_SCHEMA_TABLE_KEEP:
            out[f"{key}_truncated"] = len(tables) - _TRUNCATION_SCHEMA_TABLE_KEEP
        return out
    return _shrink_payload(value, depth=0)


def _shrink_payload(value: Any, depth: int = 0) -> Any:
    if isinstance(value, dict):
        out: dict[str, Any] = {}
        for key, item in value.items():
            if key in ("rows", "results") and isinstance(item, list):
                out[key] = _shrink_rows(item)
            elif key in ("schema", "tables") and isinstance(item, (dict, list)):
                out[key] = _shrink_schema({key: item}).get(key)
            elif key in _PRESERVE_KEYS:
                out[key] = item if not isinstance(item, (dict, list)) else _shrink_payload(item, depth + 1)
            else:
                out[key] = _shrink_payload(item, depth + 1)
        return out
    if isinstance(value, list):
        if len(value) > _TRUNCATION_LIST_KEEP:
            kept = [_shrink_payload(item, depth + 1) for item in value[:_TRUNCATION_LIST_KEEP]]
            kept.append(f"... truncated {len(value) - _TRUNCATION_LIST_KEEP} more items ...")
            return kept
        return [_shrink_payload(item, depth + 1) for item in value]
    if isinstance(value, str) and len(value) > 4000:
        return value[:4000] + f"... truncated {len(value) - 4000} more characters ..."
    return value


def _compact(value: Any) -> str:
    limit = _max_tool_result_chars()
    text = json.dumps(value, separators=(",", ":"), default=str)
    if len(text) <= limit:
        return text

    shrunk = _shrink_payload(value)
    text = json.dumps(shrunk, separators=(",", ":"), default=str)
    if len(text) <= limit:
        return text
    return json.dumps(
        {
            "truncated": True,
            "note": (
                "Result was too large; structural fields (columns, ids, validation) were preserved. "
                "Narrow the request for full row data."
            ),
            "preview": text[:limit],
        }
    )


def execute_tool(ctx: ToolContext, name: str, arguments: dict) -> str:
    handlers: dict[str, Callable[[dict], Any]] = {
        "search_queries": lambda a: ctx.request(
            "GET", "/api/queries", params={"q": a["q"], "page_size": a.get("page_size", 10)}
        ),
        "get_query": ctx.get_query_tool,
        "run_query": ctx.run_query_tool,
        "create_query": ctx.create_query_tool,
        "update_query": ctx.update_query_tool,
        "archive_query": lambda a: ctx.request("DELETE", f"/api/queries/{a['query_id']}"),
        "create_visualization": ctx.create_visualization_tool,
        "update_visualization": ctx.update_visualization_tool,
        "get_visualization": ctx.get_visualization_tool,
        "fix_query_visualizations": ctx.fix_query_visualizations_tool,
        "delete_visualization": lambda a: ctx.request("DELETE", f"/api/visualizations/{a['visualization_id']}"),
        "list_data_sources": lambda a: enrich_data_sources(ctx.request("GET", "/api/data_sources")),
        "list_query_runner_types": lambda a: platform_catalog.list_query_runner_types(a.get("q")),
        "get_query_runner_type": lambda a: _require_catalog_result(
            platform_catalog.get_query_runner_type(a["type"]),
            "Query runner type",
        ),
        "list_visualization_types": lambda a: platform_catalog.list_visualization_types(a.get("q")),
        "get_visualization_type": lambda a: _require_catalog_result(
            platform_catalog.get_visualization_type(a["type"]),
            "Visualization type",
        ),
        "get_data_source": lambda a: enrich_data_source(
            _as_dict(ctx.request("GET", f"/api/data_sources/{a['data_source_id']}"), "data source")
        ),
        "get_data_source_schema": lambda a: ctx.request(
            "GET",
            f"/api/data_sources/{a['data_source_id']}/schema",
            params={"refresh": "true"} if a.get("refresh") else None,
        ),
        "list_dashboards": lambda a: ctx.request(
            "GET",
            "/api/dashboards",
            params={k: v for k, v in {"q": a.get("q"), "page_size": a.get("page_size", 10)}.items() if v},
        ),
        "get_dashboard": ctx.get_dashboard_tool,
        "create_dashboard": lambda a: ctx.request("POST", "/api/dashboards", body={"name": a["name"]}),
        "update_dashboard": ctx.update_dashboard_tool,
        "add_widget_to_dashboard": ctx.add_widget_tool,
        "update_widget": ctx.update_widget_tool,
        "delete_widget": lambda a: ctx.request("DELETE", f"/api/widgets/{a['widget_id']}"),
        "build_dashboard_from_spec": ctx.build_dashboard_from_spec_tool,
        "refresh_queries_and_wait": ctx.refresh_queries_and_wait_tool,
        "create_multi_visualization_query": ctx.create_multi_visualization_query_tool,
        "list_alerts": lambda a: ctx.request("GET", "/api/alerts"),
        "get_alert": lambda a: ctx.request("GET", f"/api/alerts/{a['alert_id']}"),
        "get_alert_template_guide": lambda a: alert_catalog.alert_workflow(),
        "create_alert": ctx.create_alert_tool,
        "update_alert": lambda a: ctx.request(
            "POST",
            f"/api/alerts/{a['alert_id']}",
            body={k: v for k, v in a.items() if k != "alert_id" and v is not None},
        ),
        "delete_alert": lambda a: ctx.request("DELETE", f"/api/alerts/{a['alert_id']}"),
        "evaluate_alert": lambda a: ctx.request("POST", f"/api/alerts/{a['alert_id']}/eval"),
        "list_alert_subscriptions": lambda a: ctx.request("GET", f"/api/alerts/{a['alert_id']}/subscriptions"),
        "subscribe_alert": lambda a: ctx.request(
            "POST",
            f"/api/alerts/{a['alert_id']}/subscriptions",
            body={"destination_id": a["destination_id"]},
        ),
        "unsubscribe_alert": lambda a: ctx.request(
            "DELETE",
            f"/api/alerts/{a['alert_id']}/subscriptions/{a['subscription_id']}",
        ),
        "list_destinations": lambda a: ctx.request("GET", "/api/destinations"),
        "get_destination": lambda a: ctx.request("GET", f"/api/destinations/{a['destination_id']}"),
        "list_destination_types": ctx.list_destination_types_tool,
        "get_destination_type": ctx.get_destination_type_tool,
        "create_destination": lambda a: ctx.request("POST", "/api/destinations", body=_merge_body(**a)),
        "update_destination": lambda a: ctx.request(
            "POST",
            f"/api/destinations/{a['destination_id']}",
            body={k: v for k, v in a.items() if k != "destination_id" and v is not None},
        ),
        "list_ml_models": lambda a: ctx.request(
            "GET",
            "/api/ml_models",
            params={k: v for k, v in {"q": a.get("q"), "page_size": a.get("page_size", 10)}.items() if v},
        ),
        "get_ml_model": lambda a: ctx.request("GET", f"/api/ml_models/{a['model_id']}"),
        "create_ml_model": lambda a: ctx.request("POST", "/api/ml_models", body=_merge_body(**a)),
        "update_ml_model": ctx.update_ml_model_tool,
        "train_ml_model": lambda a: ctx.request("POST", f"/api/ml_models/{a['model_id']}/train"),
        "predict_ml_model": lambda a: ctx.request(
            "POST", f"/api/ml_models/{a['model_id']}/predict", body=a.get("body")
        ),
        "get_predictions": lambda a: (
            ctx.request("GET", f"/api/ml_models/{a['model_id']}/predictions")
            if a.get("model_id")
            else ctx.request("GET", "/api/predictions", params={"page_size": a.get("page_size", 10)})
        ),
        "list_indexers": lambda a: ctx.request("GET", "/api/indexers"),
        "get_indexer": lambda a: ctx.request("GET", f"/api/indexers/{a['indexer_id']}"),
        "create_indexer": lambda a: ctx.request("POST", "/api/indexers", body=_merge_body(**a)),
        "update_indexer": lambda a: ctx.request(
            "POST",
            f"/api/indexers/{a['indexer_id']}",
            body={k: v for k, v in a.items() if k != "indexer_id" and v is not None},
        ),
        "search_docs": lambda a: docs_catalog.search_docs(a["q"], ctx.help_base_url),
        "get_docs_topic": lambda a: docs_catalog.get_docs_topic(a["topic_id"], ctx.help_base_url),
        "discover_public_sources": lambda a: web_tools.discover_public_sources(
            a["topic"],
            a.get("data_kind", "json"),
            a.get("max_results", 8),
        ),
        "web_search": lambda a: web_tools.web_search(
            a["q"],
            a.get("max_results", 5),
            a.get("search_type", "general"),
            a.get("site"),
        ),
        "fetch_url": lambda a: web_tools.fetch_url(a["url"], a.get("mode", "auto")),
        "list_endpoints": lambda a: api_meta.list_endpoints(
            ctx.request, tag=a.get("tag"), search=a.get("search")
        ),
        "describe_endpoint": lambda a: api_meta.describe_endpoint(
            ctx.request, method=a["method"], path=a["path"]
        ),
        "call_api": lambda a: api_meta.call_api(
            ctx.request,
            method=a["method"],
            path=a["path"],
            query_params=a.get("query_params"),
            body=a.get("body"),
        ),
        "list_dashboard_examples": lambda a: dashboard_examples.list_dashboard_examples(a.get("q")),
        "get_dashboard_example": lambda a: dashboard_examples.get_dashboard_example(a["id"]),
        "list_instance_examples": lambda a: instance_examples.list_instance_examples(
            a.get("q"), a.get("category")
        ),
        "get_instance_example": lambda a: instance_examples.get_instance_example(a["id"]),
    }
    handler = handlers.get(name)
    if not handler:
        raise RuntimeError(f"Unknown tool {name!r}")
    try:
        payload = handler(arguments)
        try:
            payload = enrich_tool_payload(payload, ctx.base_url)
        except Exception as exc:
            logger.warning("Assistant enrich_tool_payload failed for %s: %s", name, exc)
        return _compact(payload)
    except Exception as exc:
        logger.warning("Assistant tool %s failed: %s", name, exc)
        return json.dumps({"error": str(exc)})
