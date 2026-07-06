"""OpenAI tool definitions and execution against the Rewatch API."""

from __future__ import annotations

import json
import logging
import time
from typing import Any, Callable, Optional

import requests

from rewatch.assistant import catalog as platform_catalog
from rewatch.assistant import docs as docs_catalog
from rewatch.assistant import web as web_tools
from rewatch.assistant.dashboard_layout import (
    enrich_dashboard_for_assistant,
    has_explicit_position,
    normalize_widget_options,
    suggest_next_position,
    summarize_dashboard_layout,
)
from rewatch.assistant.datasources import enrich_data_source, enrich_data_sources
from rewatch.assistant.links import enrich_tool_payload
from rewatch.assistant.visualization_helpers import (
    build_visualization_hints,
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
            "description": "Get a saved query including SQL, data source, parameters, schedule, and visualizations.",
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
                "Query syntax depends on data source type — call get_query_runner_type first."
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
                    "max_rows": {"type": "integer", "default": 50},
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
                "Update a visualization's name, type, or options. Column names in options are "
                "validated against the parent query results and auto-corrected when wrong."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "visualization_id": {"type": "integer"},
                    "name": {"type": "string"},
                    "type": {"type": "string"},
                    "options": {"type": "object"},
                    "description": {"type": "string"},
                },
                "required": ["visualization_id"],
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
    # --- Alerts ---
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
            "description": "Get one alert's configuration and state.",
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
            "description": "Create an alert on a query. op is one of >, >=, <, <=, ==, !=",
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
                },
                "required": ["name", "query_id", "column", "op", "value"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "update_alert",
            "description": "Update an alert.",
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
            "name": "list_destination_types",
            "description": "List available destination types and their configuration schemas.",
            "parameters": {"type": "object", "properties": {}},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "create_destination",
            "description": "Create a notification destination. Use list_destination_types for valid type values.",
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
    # --- Web ---
    {
        "type": "function",
        "function": {
            "name": "web_search",
            "description": "Search the public internet for documentation, APIs, SQL syntax, libraries, or current information.",
            "parameters": {
                "type": "object",
                "properties": {
                    "q": {"type": "string", "description": "Search query"},
                    "max_results": {"type": "integer", "default": 5},
                },
                "required": ["q"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "fetch_url",
            "description": "Fetch a public web page and return its readable text content.",
            "parameters": {
                "type": "object",
                "properties": {
                    "url": {"type": "string", "description": "http or https URL"},
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
        max_rows = args.get("max_rows", 50)
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
        max_rows = args.get("max_rows", 50)
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
        options = {"column": args["column"], "op": args["op"], "value": args["value"]}
        body = _merge_body(
            name=args["name"],
            query_id=args["query_id"],
            options=options,
            rearm=args.get("rearm"),
            tags=args.get("tags"),
        )
        return self.request("POST", "/api/alerts", body=body)

    def create_visualization_tool(self, args: dict) -> Any:
        query_validation = self._execute_saved_query_validation(args["query_id"])
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
        current = _as_dict(self.request("GET", f"/api/visualizations/{visualization_id}"), "visualization")
        query_id = current.get("query_id")
        corrections: list[str] = []

        if "options" in args and query_id:
            query_validation = self._execute_saved_query_validation(query_id)
            if query_validation.get("status") == "error":
                raise RuntimeError(
                    "Cannot update visualization options because the query failed to run: "
                    f"{query_validation['message']}"
                )
            viz_type = (args.get("type") or current.get("type") or "").upper()
            options, corrections = normalize_visualization_options(
                viz_type,
                args.get("options"),
                query_validation.get("columns") or [],
                query_validation.get("rows") or [],
            )
            args["options"] = options

        result = self.request("POST", f"/api/visualizations/{visualization_id}", body=_merge_body(**args))
        if corrections and isinstance(result, dict):
            result["column_corrections"] = corrections
        return result

    def get_dashboard_tool(self, args: dict) -> Any:
        dashboard = _as_dict(
            self.request("GET", f"/api/dashboards/{args['dashboard_id']}"),
            "dashboard",
        )
        return enrich_dashboard_for_assistant(dashboard)

    def add_widget_tool(self, args: dict) -> Any:
        dashboard_id = args["dashboard_id"]
        raw_options = args.get("options")
        if has_explicit_position(raw_options):
            options = normalize_widget_options(raw_options)
        else:
            dashboard = _as_dict(self.request("GET", f"/api/dashboards/{dashboard_id}"), "dashboard")
            widgets = dashboard.get("widgets") if isinstance(dashboard.get("widgets"), list) else []
            options = normalize_widget_options(raw_options, position=suggest_next_position(widgets))

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
            body["options"] = normalize_widget_options(args.pop("options"))
        if not body:
            raise RuntimeError("Provide text and/or options to update a widget.")
        return self.request("POST", f"/api/widgets/{widget_id}", body=body)


# Keep tool results within a sane share of the model context. Oversized
# payloads (huge schemas, wide query results) get structurally truncated
# instead of silently eating the whole window.
MAX_TOOL_RESULT_CHARS = 24000
_TRUNCATION_LIST_KEEP = 40


def _shrink_payload(value: Any, depth: int = 0) -> Any:
    if isinstance(value, list) and len(value) > _TRUNCATION_LIST_KEEP:
        kept = value[:_TRUNCATION_LIST_KEEP]
        return [_shrink_payload(item, depth + 1) for item in kept] + [
            f"... truncated {len(value) - _TRUNCATION_LIST_KEEP} more items ..."
        ]
    if isinstance(value, list):
        return [_shrink_payload(item, depth + 1) for item in value]
    if isinstance(value, dict):
        return {k: _shrink_payload(v, depth + 1) for k, v in value.items()}
    if isinstance(value, str) and len(value) > 4000:
        return value[:4000] + f"... truncated {len(value) - 4000} more characters ..."
    return value


def _compact(value: Any) -> str:
    text = json.dumps(value, separators=(",", ":"), default=str)
    if len(text) <= MAX_TOOL_RESULT_CHARS:
        return text

    shrunk = _shrink_payload(value)
    text = json.dumps(shrunk, separators=(",", ":"), default=str)
    if len(text) <= MAX_TOOL_RESULT_CHARS:
        return text
    return json.dumps(
        {
            "truncated": True,
            "note": "Result was too large; showing a prefix. Narrow the request (fewer rows/fields) for full data.",
            "preview": text[:MAX_TOOL_RESULT_CHARS],
        }
    )


def execute_tool(ctx: ToolContext, name: str, arguments: dict) -> str:
    handlers: dict[str, Callable[[dict], Any]] = {
        "search_queries": lambda a: ctx.request(
            "GET", "/api/queries", params={"q": a["q"], "page_size": a.get("page_size", 10)}
        ),
        "get_query": lambda a: ctx.request("GET", f"/api/queries/{a['query_id']}"),
        "run_query": ctx.run_query_tool,
        "create_query": ctx.create_query_tool,
        "update_query": ctx.update_query_tool,
        "archive_query": lambda a: ctx.request("DELETE", f"/api/queries/{a['query_id']}"),
        "create_visualization": ctx.create_visualization_tool,
        "update_visualization": ctx.update_visualization_tool,
        "delete_visualization": lambda a: ctx.request("DELETE", f"/api/visualizations/{a['visualization_id']}"),
        "list_data_sources": lambda a: enrich_data_sources(ctx.request("GET", "/api/data_sources")),
        "list_query_runner_types": lambda a: platform_catalog.list_query_runner_types(a.get("q")),
        "get_query_runner_type": lambda a: platform_catalog.get_query_runner_type(a["type"]),
        "list_visualization_types": lambda a: platform_catalog.list_visualization_types(a.get("q")),
        "get_visualization_type": lambda a: platform_catalog.get_visualization_type(a["type"]),
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
        "list_alerts": lambda a: ctx.request("GET", "/api/alerts"),
        "get_alert": lambda a: ctx.request("GET", f"/api/alerts/{a['alert_id']}"),
        "create_alert": ctx.create_alert_tool,
        "update_alert": lambda a: ctx.request(
            "POST",
            f"/api/alerts/{a['alert_id']}",
            body={k: v for k, v in a.items() if k != "alert_id" and v is not None},
        ),
        "delete_alert": lambda a: ctx.request("DELETE", f"/api/alerts/{a['alert_id']}"),
        "list_destinations": lambda a: ctx.request("GET", "/api/destinations"),
        "list_destination_types": lambda a: ctx.request("GET", "/api/destinations/types"),
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
        "web_search": lambda a: web_tools.web_search(a["q"], a.get("max_results", 5)),
        "fetch_url": lambda a: web_tools.fetch_url(a["url"]),
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
