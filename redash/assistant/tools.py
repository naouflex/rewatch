"""OpenAI tool definitions and execution against the Rewatch API."""

from __future__ import annotations

import json
import time
from typing import Any, Callable, Optional

import requests

from redash.assistant import docs as docs_catalog

JOB_FINISHED = 3
JOB_FAILED = 4
JOB_CANCELED = 5

TOOL_DEFINITIONS: list[dict[str, Any]] = [
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
            "description": "Get a saved query including its SQL, data source, parameters, and schedule.",
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
            "description": "Execute a saved query or ad-hoc SQL and return result rows.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query_id": {"type": "integer", "description": "Saved query ID"},
                    "query_text": {"type": "string", "description": "Ad-hoc SQL when query_id is omitted"},
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
            "description": "Create a new saved query (starts as draft).",
            "parameters": {
                "type": "object",
                "properties": {
                    "name": {"type": "string"},
                    "query": {"type": "string", "description": "SQL text"},
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
            "description": "Update an existing saved query.",
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
            "name": "list_data_sources",
            "description": "List connected data sources (id, name, type).",
            "parameters": {"type": "object", "properties": {}},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_data_source_schema",
            "description": "Get tables and columns for a data source.",
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
            "description": "Get a dashboard with widgets and linked queries.",
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
            "description": "Create a new dashboard.",
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
            "description": "Update a dashboard name, layout, tags, or draft status.",
            "parameters": {
                "type": "object",
                "properties": {
                    "dashboard_id": {"type": "integer"},
                    "name": {"type": "string"},
                    "layout": {"type": "array"},
                    "tags": {"type": "array", "items": {"type": "string"}},
                    "is_draft": {"type": "boolean"},
                },
                "required": ["dashboard_id"],
            },
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
            job = self.request("GET", f"/api/jobs/{job_id}")["job"]
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
            result_id = self.poll_job(response["job"])
            if query_id is not None:
                response = self.request("GET", f"/api/queries/{query_id}/results/{result_id}.json")
            else:
                response = self.request("GET", f"/api/query_results/{result_id}")

        query_result = response.get("query_result") or {}
        rows = query_result.get("data", {}).get("rows", [])
        columns = [c.get("name") for c in query_result.get("data", {}).get("columns", [])]
        return {
            "query_result_id": query_result.get("id"),
            "columns": columns,
            "row_count": len(rows),
            "rows": rows[:max_rows],
            "note": f"Showing first {max_rows} rows" if len(rows) > max_rows else None,
        }

    def create_query_tool(self, args: dict) -> Any:
        body = {k: v for k, v in args.items() if v is not None}
        return self.request("POST", "/api/queries", body=body)

    def update_query_tool(self, args: dict) -> Any:
        args = dict(args)
        query_id = args.pop("query_id")
        current = self.request("GET", f"/api/queries/{query_id}")
        body = {k: v for k, v in args.items() if v is not None}
        body.setdefault("version", current.get("version"))
        return self.request("POST", f"/api/queries/{query_id}", body=body)

    def update_dashboard_tool(self, args: dict) -> Any:
        args = dict(args)
        dashboard_id = args.pop("dashboard_id")
        current = self.request("GET", f"/api/dashboards/{dashboard_id}")
        body = {k: v for k, v in args.items() if v is not None}
        body.setdefault("version", current.get("version"))
        return self.request("POST", f"/api/dashboards/{dashboard_id}", body=body)

    def create_alert_tool(self, args: dict) -> Any:
        options = {"column": args["column"], "op": args["op"], "value": args["value"]}
        body = {
            "name": args["name"],
            "query_id": args["query_id"],
            "options": options,
        }
        if args.get("rearm") is not None:
            body["rearm"] = args["rearm"]
        if args.get("tags"):
            body["tags"] = args["tags"]
        return self.request("POST", "/api/alerts", body=body)


def _compact(value: Any) -> str:
    return json.dumps(value, indent=2, default=str)


def execute_tool(ctx: ToolContext, name: str, arguments: dict) -> str:
    handlers: dict[str, Callable[[dict], Any]] = {
        "search_queries": lambda a: ctx.request(
            "GET", "/api/queries", params={"q": a["q"], "page_size": a.get("page_size", 10)}
        ),
        "get_query": lambda a: ctx.request("GET", f"/api/queries/{a['query_id']}"),
        "run_query": ctx.run_query_tool,
        "create_query": ctx.create_query_tool,
        "update_query": ctx.update_query_tool,
        "list_data_sources": lambda a: ctx.request("GET", "/api/data_sources"),
        "get_data_source_schema": lambda a: ctx.request("GET", f"/api/data_sources/{a['data_source_id']}/schema"),
        "list_dashboards": lambda a: ctx.request(
            "GET", "/api/dashboards", params={k: v for k, v in {"q": a.get("q"), "page_size": a.get("page_size", 10)}.items() if v}
        ),
        "get_dashboard": lambda a: ctx.request("GET", f"/api/dashboards/{a['dashboard_id']}"),
        "create_dashboard": lambda a: ctx.request("POST", "/api/dashboards", body={"name": a["name"]}),
        "update_dashboard": ctx.update_dashboard_tool,
        "list_alerts": lambda a: ctx.request("GET", "/api/alerts"),
        "get_alert": lambda a: ctx.request("GET", f"/api/alerts/{a['alert_id']}"),
        "create_alert": ctx.create_alert_tool,
        "update_alert": lambda a: ctx.request(
            "POST",
            f"/api/alerts/{a['alert_id']}",
            body={k: v for k, v in a.items() if k != "alert_id" and v is not None},
        ),
        "search_docs": lambda a: docs_catalog.search_docs(a["q"], ctx.help_base_url),
        "get_docs_topic": lambda a: docs_catalog.get_docs_topic(a["topic_id"], ctx.help_base_url),
    }
    handler = handlers.get(name)
    if not handler:
        raise RuntimeError(f"Unknown tool {name!r}")
    try:
        return _compact(handler(arguments))
    except Exception as exc:
        return json.dumps({"error": str(exc)})
