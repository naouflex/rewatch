"""FastMCP stdio server exposing the Rewatch (Rewatch) REST API.

Design: three *meta* tools (``list_endpoints`` / ``describe_endpoint`` /
``call_api``) give full coverage of every route in the live OpenAPI spec
served at ``/api/spec``, and a handful of curated tools wrap the workflows
agents use most (running queries, browsing schemas, dashboards, alerts,
ML models).

Configuration (environment variables):

* ``REWATCH_BASE_URL``      — base URL of the instance (default ``http://localhost:5001``)
* ``REWATCH_API_KEY``       — required; user API key from the Rewatch UI
* ``REWATCH_MCP_READ_ONLY`` — when truthy, ``call_api`` rejects non-GET methods
"""

from __future__ import annotations

import json
import os
import time
from pathlib import Path
from typing import Any, Optional

import httpx
from dotenv import load_dotenv
from mcp.server.fastmcp import FastMCP

try:
    from rewatch_mcp.alert_catalog import alert_catalog
except ImportError:
    alert_catalog = None  # type: ignore[assignment]

try:
    from rewatch_mcp.platform_catalog import platform_catalog
except ImportError:
    platform_catalog = None  # type: ignore[assignment]

_WORKSPACE_ENV = Path(__file__).resolve().parent.parent.parent / ".env"
if _WORKSPACE_ENV.is_file():
    load_dotenv(_WORKSPACE_ENV, override=False)

BASE_URL = os.environ.get("REWATCH_BASE_URL", "http://localhost:5001").rstrip("/")
API_KEY = os.environ.get("REWATCH_API_KEY", "")
READ_ONLY = os.environ.get("REWATCH_MCP_READ_ONLY", "").lower() in ("1", "true", "yes")

# Job statuses from rewatch.serializers.serialize_job
JOB_FINISHED = 3
JOB_FAILED = 4
JOB_CANCELED = 5

mcp = FastMCP(
    "rewatch",
    instructions=(
        "Tools for the Rewatch (Rewatch) data platform: run SQL queries, create and "
        "update queries/alerts/dashboards/ML models, browse data sources and schemas, "
        "configure notification destinations (Slack, webhooks, Discord, email, …), "
        "and call any REST API endpoint. For alerts: run_query first to validate columns, "
        "get_destination_type for webhook template examples, create_destination, then "
        "create_alert with destination_ids to subscribe. Use list_endpoints/describe_endpoint "
        "to discover the full API surface, then call_api for anything not covered by a "
        "dedicated tool."
    ),
)

_client: Optional[httpx.Client] = None
_spec_cache: Optional[dict] = None


def _http() -> httpx.Client:
    global _client
    if _client is None:
        if not API_KEY:
            raise RuntimeError("REWATCH_API_KEY environment variable is not set")
        _client = httpx.Client(
            base_url=BASE_URL,
            headers={"Authorization": f"Key {API_KEY}"},
            timeout=60.0,
            follow_redirects=True,
        )
    return _client


def _request(method: str, path: str, *, params: Optional[dict] = None, body: Optional[dict] = None) -> Any:
    """Perform an API request and return parsed JSON, raising a readable error on failure."""
    if not path.startswith("/"):
        path = "/" + path
    resp = _http().request(method.upper(), path, params=params, json=body)
    if resp.status_code >= 400:
        detail = resp.text[:2000]
        raise RuntimeError(f"{method.upper()} {path} failed with HTTP {resp.status_code}: {detail}")
    if not resp.content:
        return {"status_code": resp.status_code}
    try:
        return resp.json()
    except ValueError:
        return {"status_code": resp.status_code, "text": resp.text[:10000]}


def _spec() -> dict:
    global _spec_cache
    if _spec_cache is None:
        _spec_cache = _request("GET", "/api/spec")
    return _spec_cache


def _compact(obj: Any) -> str:
    return json.dumps(obj, indent=2, default=str)


def _ensure_writable() -> None:
    if READ_ONLY:
        raise RuntimeError("This MCP server is running in read-only mode (REWATCH_MCP_READ_ONLY); writes are disabled.")


def _merge_body(**fields: Any) -> dict[str, Any]:
    return {key: value for key, value in fields.items() if value is not None}


def _require_catalog_result(result: Any, label: str = "lookup") -> Any:
    if isinstance(result, dict) and result.get("error"):
        known = result.get("known_types")
        suffix = f" Known types: {known[:25]}" if isinstance(known, list) and known else ""
        raise RuntimeError(f"{label} failed: {result['error']}{suffix}")
    return result


def _require_widget_content(visualization_id: Optional[int], text: Optional[str]) -> None:
    if visualization_id is None and not text:
        raise RuntimeError("Provide visualization_id (chart/table widget) or text (text box widget).")


def _run_saved_query_result(query_id: int, max_age: int = -1) -> dict[str, Any]:
    """Execute a saved query and return the API response containing query_result."""
    try:
        response = _request("POST", f"/api/queries/{query_id}/results", body={"max_age": max_age})
        if "job" in response:
            result_id = _poll_job(response["job"], 120)
            response = _request("GET", f"/api/queries/{query_id}/results/{result_id}.json")
        return response
    except RuntimeError as exc:
        message = str(exc)
        if "Missing parameter" in message or "missing parameter" in message.lower():
            raise RuntimeError(
                f"Query #{query_id} requires parameter values. "
                "Run run_query(query_id=..., parameters={{...}}) first or set defaults on the query."
            ) from exc
        raise RuntimeError(f"Query #{query_id} must run successfully: {message}") from exc


# ---------------------------------------------------------------------------
# Meta tools: full API coverage via the live OpenAPI spec
# ---------------------------------------------------------------------------


@mcp.tool()
def list_endpoints(tag: Optional[str] = None, search: Optional[str] = None) -> str:
    """Browse the catalog of all Rewatch REST API endpoints.

    Returns one line per operation: METHOD, path, tag and summary. Optionally
    filter by tag (e.g. "Queries", "Dashboards", "MLModels", "DataSources",
    "Alerts", "Users") or by a free-text search over path and summary.
    Use describe_endpoint for parameter details and call_api to invoke one.
    """
    spec = _spec()
    lines = []
    for path, ops in spec.get("paths", {}).items():
        for method, op in ops.items():
            op_tag = (op.get("tags") or ["Misc"])[0]
            summary = op.get("summary", "")
            if tag and op_tag.lower() != tag.lower():
                continue
            if search:
                haystack = f"{path} {summary} {op_tag}".lower()
                if search.lower() not in haystack:
                    continue
            lines.append(f"{method.upper():6} {path}  [{op_tag}] {summary}")
    if not lines:
        available = sorted({t["name"] for t in _spec().get("tags", [])})
        return f"No endpoints matched. Available tags: {', '.join(available)}"
    return "\n".join(sorted(lines))


@mcp.tool()
def describe_endpoint(method: str, path: str) -> str:
    """Get full details for one API operation: parameters, request body schema and responses.

    ``path`` must match the spec's template form, e.g. "/api/queries/{query_id}".
    Use list_endpoints first to find the exact path.
    """
    spec = _spec()
    ops = spec.get("paths", {}).get(path)
    if ops is None:
        # Help with near-misses (trailing slash, missing /api prefix).
        candidates = [p for p in spec.get("paths", {}) if path.strip("/") in p]
        hint = f" Did you mean one of: {', '.join(candidates[:10])}?" if candidates else ""
        raise RuntimeError(f"Unknown path {path!r}.{hint}")
    op = ops.get(method.lower())
    if op is None:
        raise RuntimeError(f"Path {path} does not support {method.upper()}. Available: {', '.join(m.upper() for m in ops)}")
    return _compact(op)


@mcp.tool()
def call_api(
    method: str,
    path: str,
    query_params: Optional[dict] = None,
    body: Optional[dict] = None,
) -> str:
    """Invoke any Rewatch REST API endpoint and return the JSON response.

    ``path`` is the concrete URL path with real values substituted, e.g.
    "/api/queries/42" (not "{query_id}"). ``query_params`` become URL query
    parameters; ``body`` is sent as the JSON request body for POST/DELETE.
    Prefer the dedicated tools (run_query, get_query, ...) when they fit.
    """
    if READ_ONLY and method.upper() != "GET":
        raise RuntimeError("This MCP server is running in read-only mode (REWATCH_MCP_READ_ONLY); only GET is allowed.")
    if "{" in path:
        raise RuntimeError(f"Path {path!r} still contains a template placeholder; substitute real values first.")
    return _compact(_request(method, path, params=query_params, body=body))


# ---------------------------------------------------------------------------
# Query execution
# ---------------------------------------------------------------------------


def _poll_job(job: dict, timeout_seconds: int) -> int:
    """Poll a background job until it finishes; return the query result id."""
    deadline = time.monotonic() + timeout_seconds
    job_id = job["id"]
    while time.monotonic() < deadline:
        status = job.get("status")
        if status == JOB_FINISHED:
            result_id = job.get("query_result_id") or job.get("result")
            if not result_id:
                raise RuntimeError(f"Job {job_id} finished but returned no query result id: {job}")
            return result_id
        if status in (JOB_FAILED, JOB_CANCELED):
            raise RuntimeError(f"Query execution failed: {job.get('error') or job}")
        time.sleep(1)
        job = _request("GET", f"/api/jobs/{job_id}")["job"]
    raise RuntimeError(f"Query did not finish within {timeout_seconds}s (job {job_id} status {job.get('status')}).")


def _format_query_result(query_result: dict, max_rows: int) -> str:
    data = query_result.get("data", {})
    rows = data.get("rows", [])
    columns = [c.get("name") for c in data.get("columns", [])]
    out = {
        "query_result_id": query_result.get("id"),
        "retrieved_at": query_result.get("retrieved_at"),
        "runtime_seconds": query_result.get("runtime"),
        "columns": columns,
        "row_count": len(rows),
        "rows": rows[:max_rows],
    }
    if len(rows) > max_rows:
        out["note"] = f"Showing first {max_rows} of {len(rows)} rows."
    return _compact(out)


@mcp.tool()
def run_query(
    query_id: Optional[int] = None,
    query_text: Optional[str] = None,
    data_source_id: Optional[int] = None,
    parameters: Optional[dict] = None,
    max_age: int = -1,
    max_rows: int = 100,
    timeout_seconds: int = 120,
) -> str:
    """Execute a query and return its result rows.

    Two modes:
    * Saved query: pass ``query_id`` (plus ``parameters`` if the query is parameterized).
    * Ad-hoc query: pass ``query_text`` and ``data_source_id``.

    ``max_age`` controls caching: -1 returns any cached result (executing only
    if none exists), 0 forces execution, N accepts results up to N seconds old.
    Handles the background-job polling automatically.
    """
    if query_id is not None:
        body: dict[str, Any] = {"max_age": max_age}
        if parameters:
            body["parameters"] = parameters
        response = _request("POST", f"/api/queries/{query_id}/results", body=body)
    elif query_text and data_source_id:
        body = {
            "query": query_text,
            "data_source_id": data_source_id,
            "max_age": max_age,
            "parameters": parameters or {},
            "apply_auto_limit": True,
        }
        response = _request("POST", "/api/query_results", body=body)
    else:
        raise RuntimeError("Pass either query_id (saved query) or query_text + data_source_id (ad-hoc query).")

    if "job" in response:
        result_id = _poll_job(response["job"], timeout_seconds)
        if query_id is not None:
            response = _request("GET", f"/api/queries/{query_id}/results/{result_id}.json")
        else:
            response = _request("GET", f"/api/query_results/{result_id}")

    query_result = response.get("query_result")
    if not query_result:
        raise RuntimeError(f"Unexpected response: {_compact(response)[:2000]}")
    return _format_query_result(query_result, max_rows)


# ---------------------------------------------------------------------------
# Queries
# ---------------------------------------------------------------------------


@mcp.tool()
def search_queries(q: str, page: int = 1, page_size: int = 25) -> str:
    """Search saved queries by name/description/query text. Returns id, name and data source per match."""
    response = _request("GET", "/api/queries", params={"q": q, "page": page, "page_size": page_size})
    results = [
        {
            "id": item["id"],
            "name": item.get("name"),
            "data_source_id": item.get("data_source_id"),
            "is_archived": item.get("is_archived"),
            "updated_at": item.get("updated_at"),
        }
        for item in response.get("results", [])
    ]
    return _compact({"count": response.get("count"), "page": response.get("page"), "results": results})


@mcp.tool()
def get_query(query_id: int) -> str:
    """Get a saved query: its SQL text, data source, parameters, schedule and visualizations."""
    return _compact(_request("GET", f"/api/queries/{query_id}"))


@mcp.tool()
def create_query(
    name: str,
    query: str,
    data_source_id: int,
    description: Optional[str] = None,
    schedule: Optional[dict] = None,
    options: Optional[dict] = None,
    tags: Optional[list[str]] = None,
) -> str:
    """Create a new saved query (starts as a draft).

    ``query`` is the SQL text. ``data_source_id`` comes from list_data_sources.
    ``schedule`` example: ``{"interval": 3600, "time": null, "day_of_week": null, "until": null}``.
    """
    _ensure_writable()
    body = _merge_body(
        name=name,
        query=query,
        data_source_id=data_source_id,
        description=description,
        schedule=schedule,
        options=options,
        tags=tags,
    )
    return _compact(_request("POST", "/api/queries", body=body))


@mcp.tool()
def update_query(
    query_id: int,
    name: Optional[str] = None,
    query: Optional[str] = None,
    data_source_id: Optional[int] = None,
    description: Optional[str] = None,
    schedule: Optional[dict] = None,
    options: Optional[dict] = None,
    tags: Optional[list[str]] = None,
    is_draft: Optional[bool] = None,
    version: Optional[int] = None,
) -> str:
    """Update a saved query. Fetches the current version automatically unless you pass one."""
    _ensure_writable()
    current = _request("GET", f"/api/queries/{query_id}")
    body = _merge_body(
        name=name,
        query=query,
        data_source_id=data_source_id,
        description=description,
        schedule=schedule,
        options=options,
        tags=tags,
        is_draft=is_draft,
        version=version if version is not None else current.get("version"),
    )
    return _compact(_request("POST", f"/api/queries/{query_id}", body=body))


@mcp.tool()
def archive_query(query_id: int) -> str:
    """Archive (soft-delete) a query."""
    _ensure_writable()
    _request("DELETE", f"/api/queries/{query_id}")
    return _compact({"archived": True, "query_id": query_id})


# ---------------------------------------------------------------------------
# Data sources
# ---------------------------------------------------------------------------


@mcp.tool()
def list_data_sources() -> str:
    """List connected data sources (id, name, type). Needed to run ad-hoc queries."""
    return _compact(_request("GET", "/api/data_sources"))


@mcp.tool()
def get_data_source_schema(data_source_id: int, refresh: bool = False) -> str:
    """Get the table/column schema of a data source. Set refresh=true to bypass the schema cache."""
    params = {"refresh": "true"} if refresh else None
    return _compact(_request("GET", f"/api/data_sources/{data_source_id}/schema", params=params))


@mcp.tool()
def list_query_runner_types(q: Optional[str] = None) -> str:
    """List query runner types (pg, mysql, coingecko, defillama, …) with syntax hints.

    Call get_query_runner_type(type) before writing query text for an unfamiliar source.
    """
    if platform_catalog is None:
        raise RuntimeError("Platform catalog is unavailable in this MCP install.")
    return _compact(platform_catalog.list_query_runner_types(q))


@mcp.tool()
def get_query_runner_type(type: str) -> str:
    """Get syntax guide, config fields, and examples for one query runner type."""
    if platform_catalog is None:
        raise RuntimeError("Platform catalog is unavailable in this MCP install.")
    return _compact(_require_catalog_result(platform_catalog.get_query_runner_type(type), "Query runner type"))


@mcp.tool()
def list_visualization_types(q: Optional[str] = None) -> str:
    """List visualization types (TABLE, CHART, COUNTER, DETAILS, …)."""
    if platform_catalog is None:
        raise RuntimeError("Platform catalog is unavailable in this MCP install.")
    return _compact(platform_catalog.list_visualization_types(q))


@mcp.tool()
def get_visualization_type(type: str) -> str:
    """Get option schema and workflow tips for one visualization type."""
    if platform_catalog is None:
        raise RuntimeError("Platform catalog is unavailable in this MCP install.")
    return _compact(_require_catalog_result(platform_catalog.get_visualization_type(type), "Visualization type"))


# ---------------------------------------------------------------------------
# Dashboards
# ---------------------------------------------------------------------------


@mcp.tool()
def list_dashboards(q: Optional[str] = None, page: int = 1, page_size: int = 25) -> str:
    """List or search dashboards. Returns id, slug, name and tags per dashboard."""
    params: dict[str, Any] = {"page": page, "page_size": page_size}
    if q:
        params["q"] = q
    response = _request("GET", "/api/dashboards", params=params)
    results = [
        {
            "id": item["id"],
            "slug": item.get("slug"),
            "name": item.get("name"),
            "tags": item.get("tags"),
            "is_archived": item.get("is_archived"),
            "updated_at": item.get("updated_at"),
        }
        for item in response.get("results", [])
    ]
    return _compact({"count": response.get("count"), "page": response.get("page"), "results": results})


@mcp.tool()
def get_dashboard(dashboard_id: int) -> str:
    """Get a dashboard with its widgets and the queries/visualizations they reference."""
    return _compact(_request("GET", f"/api/dashboards/{dashboard_id}"))


@mcp.tool()
def create_dashboard(name: str) -> str:
    """Create a new dashboard (starts as a draft with an empty layout)."""
    _ensure_writable()
    return _compact(_request("POST", "/api/dashboards", body={"name": name}))


@mcp.tool()
def update_dashboard(
    dashboard_id: int,
    name: Optional[str] = None,
    layout: Optional[list] = None,
    tags: Optional[list[str]] = None,
    is_draft: Optional[bool] = None,
    is_archived: Optional[bool] = None,
    dashboard_filters_enabled: Optional[bool] = None,
    options: Optional[dict] = None,
    version: Optional[int] = None,
) -> str:
    """Update a dashboard. Fetches the current version automatically unless you pass one."""
    _ensure_writable()
    current = _request("GET", f"/api/dashboards/{dashboard_id}")
    body = _merge_body(
        name=name,
        layout=layout,
        tags=tags,
        is_draft=is_draft,
        is_archived=is_archived,
        dashboard_filters_enabled=dashboard_filters_enabled,
        options=options,
        version=version if version is not None else current.get("version"),
    )
    return _compact(_request("POST", f"/api/dashboards/{dashboard_id}", body=body))


# ---------------------------------------------------------------------------
# Alerts
# ---------------------------------------------------------------------------


def _validate_alert_column_from_query(query_id: int, column: str) -> dict[str, Any]:
    """Run the linked query and verify the threshold column exists."""
    if alert_catalog is None:
        return {"skipped": True}
    response = _run_saved_query_result(query_id)
    query_result = response.get("query_result", {})
    columns = [c.get("name") for c in query_result.get("data", {}).get("columns", []) if c.get("name")]
    return alert_catalog.validate_alert_column(column, columns)


def _subscribe_alert_destinations(alert_id: int, destination_ids: list[int]) -> list[dict[str, Any]]:
    subscriptions = []
    for destination_id in destination_ids:
        subscriptions.append(
            _request("POST", f"/api/alerts/{alert_id}/subscriptions", body={"destination_id": destination_id})
        )
    return subscriptions


@mcp.tool()
def list_alerts() -> str:
    """List alerts with their state (ok/triggered/unknown), linked query and options."""
    return _compact(_request("GET", "/api/alerts"))


@mcp.tool()
def get_alert(alert_id: int) -> str:
    """Get one alert: trigger condition, state, linked query, templates and rearm settings."""
    return _compact(_request("GET", f"/api/alerts/{alert_id}"))


@mcp.tool()
def get_alert_template_guide() -> str:
    """Mustache variables and workflow for alert notification templates (custom_subject / custom_body).

    Use before writing webhook or Discord custom payloads. For destination-specific JSON
    examples, call get_destination_type(type='webhook' or 'discord_webhook').
    """
    if alert_catalog is None:
        raise RuntimeError("Alert template guide is unavailable in this MCP install.")
    return _compact(alert_catalog.alert_workflow())


@mcp.tool()
def create_alert(
    name: str,
    query_id: int,
    column: str,
    op: str,
    value: Any,
    rearm: Optional[int] = None,
    tags: Optional[list[str]] = None,
    muted: bool = False,
    selector: str = "first",
    custom_subject: Optional[str] = None,
    custom_body: Optional[str] = None,
    send_for_each_row: bool = False,
    destination_ids: Optional[list[int]] = None,
    validate_column: bool = True,
) -> str:
    """Create an alert on a saved query and optionally subscribe notification destinations.

  ``op`` is one of: ``>``, ``>=``, ``<``, ``<=``, ``==``, ``!=``.
  ``selector``: ``first`` (default), ``min``, or ``max`` across result rows.
  ``custom_subject`` / ``custom_body``: Mustache templates for notification text (see get_alert_template_guide).
  ``send_for_each_row``: notify once per query result row (use QUERY_RESULT_ROW in templates).
  ``destination_ids``: destination IDs to subscribe immediately after creation.
  Set ``validate_column=false`` to skip the pre-flight column check against query results.
    """
    _ensure_writable()
    column_check: dict[str, Any] = {}
    resolved_column = column
    if validate_column and alert_catalog is not None:
        column_check = _validate_alert_column_from_query(query_id, column)
        if not column_check.get("valid"):
            raise RuntimeError(
                f"Alert column validation failed: {column_check.get('message')}. "
                f"Available columns: {column_check.get('available_columns')}. "
                "Run run_query(query_id=...) first or pass validate_column=false."
            )
        resolved_column = column_check.get("column", column)

    if alert_catalog is not None:
        try:
            options = alert_catalog.build_alert_options(
                column=resolved_column,
                op=op,
                value=value,
                selector=selector,
                custom_subject=custom_subject,
                custom_body=custom_body,
                send_for_each_row=send_for_each_row,
                muted=muted,
            )
        except ValueError as exc:
            raise RuntimeError(str(exc)) from exc
    else:
        options = {"column": resolved_column, "op": op, "value": value, "selector": selector}
        if custom_subject:
            options["custom_subject"] = custom_subject
        if custom_body:
            options["custom_body"] = custom_body
        if send_for_each_row:
            options["send_for_each_row"] = True
        if muted:
            options["muted"] = True

    body = _merge_body(name=name, query_id=query_id, options=options, rearm=rearm, tags=tags)
    alert = _request("POST", "/api/alerts", body=body)

    result: dict[str, Any] = {"alert": alert}
    if column_check:
        result["column_validation"] = column_check
    if destination_ids:
        result["subscriptions"] = _subscribe_alert_destinations(alert["id"], destination_ids)
    return _compact(result)


@mcp.tool()
def update_alert(
    alert_id: int,
    name: Optional[str] = None,
    query_id: Optional[int] = None,
    options: Optional[dict] = None,
    rearm: Optional[int] = None,
    tags: Optional[list[str]] = None,
) -> str:
    """Update an alert's name, linked query, trigger options (incl. custom_body/custom_subject), rearm or tags."""
    _ensure_writable()
    body = _merge_body(name=name, query_id=query_id, options=options, rearm=rearm, tags=tags)
    return _compact(_request("POST", f"/api/alerts/{alert_id}", body=body))


@mcp.tool()
def delete_alert(alert_id: int) -> str:
    """Permanently delete an alert."""
    _ensure_writable()
    _request("DELETE", f"/api/alerts/{alert_id}")
    return _compact({"deleted": True, "alert_id": alert_id})


@mcp.tool()
def evaluate_alert(alert_id: int) -> str:
    """Manually evaluate an alert against its query's latest results and send notifications if triggered."""
    _ensure_writable()
    _request("POST", f"/api/alerts/{alert_id}/eval")
    return _compact({"evaluated": True, "alert_id": alert_id})


@mcp.tool()
def list_alert_subscriptions(alert_id: int) -> str:
    """List notification destinations subscribed to an alert."""
    return _compact(_request("GET", f"/api/alerts/{alert_id}/subscriptions"))


@mcp.tool()
def subscribe_alert(alert_id: int, destination_id: int) -> str:
    """Subscribe a notification destination to an alert."""
    _ensure_writable()
    return _compact(
        _request("POST", f"/api/alerts/{alert_id}/subscriptions", body={"destination_id": destination_id})
    )


@mcp.tool()
def unsubscribe_alert(alert_id: int, subscription_id: int) -> str:
    """Remove a destination subscription from an alert."""
    _ensure_writable()
    _request("DELETE", f"/api/alerts/{alert_id}/subscriptions/{subscription_id}")
    return _compact({"unsubscribed": True, "alert_id": alert_id, "subscription_id": subscription_id})


# ---------------------------------------------------------------------------
# ML models (Rewatch extension)
# ---------------------------------------------------------------------------


@mcp.tool()
def list_ml_models(q: Optional[str] = None, page: int = 1, page_size: int = 25) -> str:
    """List or search ML models (Rewatch extension). Returns model metadata and training state."""
    params: dict[str, Any] = {"page": page, "page_size": page_size}
    if q:
        params["q"] = q
    return _compact(_request("GET", "/api/ml_models", params=params))


@mcp.tool()
def get_ml_model(model_id: int) -> str:
    """Get one ML model: configuration, linked query, training state and latest version."""
    return _compact(_request("GET", f"/api/ml_models/{model_id}"))


@mcp.tool()
def create_ml_model(
    name: str,
    query_id: int,
    options: dict,
    description: Optional[str] = None,
    tags: Optional[list[str]] = None,
) -> str:
    """Create an ML model bound to a query.

    ``options`` must include at least ``regressor``, ``features`` and ``targets``.
    Example: ``{"regressor": "RandomForestRegressor", "features": ["x"], "targets": ["y"]}``.
    """
    _ensure_writable()
    body = _merge_body(name=name, query_id=query_id, options=options, description=description, tags=tags)
    return _compact(_request("POST", "/api/ml_models", body=body))


@mcp.tool()
def update_ml_model(
    model_id: int,
    name: Optional[str] = None,
    description: Optional[str] = None,
    options: Optional[dict] = None,
    tags: Optional[list[str]] = None,
    version: Optional[int] = None,
) -> str:
    """Update an ML model definition. Fetches the current version automatically unless you pass one."""
    _ensure_writable()
    current = _request("GET", f"/api/ml_models/{model_id}")
    body = _merge_body(
        name=name,
        description=description,
        options=options,
        tags=tags,
        version=version if version is not None else current.get("version"),
    )
    return _compact(_request("POST", f"/api/ml_models/{model_id}", body=body))


@mcp.tool()
def train_ml_model(model_id: int) -> str:
    """Start a training run for an ML model. Returns the training job info; training is asynchronous."""
    _ensure_writable()
    return _compact(_request("POST", f"/api/ml_models/{model_id}/train"))


@mcp.tool()
def predict_ml_model(model_id: int, body: Optional[dict] = None) -> str:
    """Start a prediction run for a trained ML model. Prediction is asynchronous; results appear under get_predictions."""
    _ensure_writable()
    return _compact(_request("POST", f"/api/ml_models/{model_id}/predict", body=body))


@mcp.tool()
def get_predictions(model_id: Optional[int] = None, page: int = 1, page_size: int = 25) -> str:
    """List stored prediction results, optionally scoped to one ML model."""
    if model_id is not None:
        return _compact(_request("GET", f"/api/ml_models/{model_id}/predictions"))
    return _compact(_request("GET", "/api/predictions", params={"page": page, "page_size": page_size}))


# ---------------------------------------------------------------------------
# Destinations (alert/ML notification targets)
# ---------------------------------------------------------------------------


@mcp.tool()
def list_destinations() -> str:
    """List notification destinations (Slack, email, webhooks, etc.)."""
    return _compact(_request("GET", "/api/destinations"))


@mcp.tool()
def get_destination(destination_id: int) -> str:
    """Get one notification destination including type, options and tags."""
    return _compact(_request("GET", f"/api/destinations/{destination_id}"))


@mcp.tool()
def list_destination_types(query: Optional[str] = None) -> str:
    """List available destination types with configuration schemas and template summaries.

    For webhook/Discord template examples and Mustache variables, call get_destination_type.
    """
    api_types = _request("GET", "/api/destinations/types")
    if alert_catalog is not None:
        return _compact(alert_catalog.list_destination_types_catalog(api_types, query=query))
    return _compact(api_types)


@mcp.tool()
def get_destination_type(type: str) -> str:
    """Get full docs for one destination type: config schema, template location, and examples.

    ``type`` examples: ``webhook``, ``discord_webhook``, ``slack``, ``microsoft_teams_webhook``, ``email``.
    Alert-level templates use Mustache (custom_subject/custom_body). Teams uses destination message_template.
    """
    api_entry = None
    for entry in _request("GET", "/api/destinations/types"):
        if entry.get("type") == type:
            api_entry = entry
            break
    if alert_catalog is not None:
        return _compact(
            _require_catalog_result(alert_catalog.get_destination_type(type, api_entry), "Destination type")
        )
    if api_entry is None:
        raise RuntimeError(f"Unknown destination type {type!r}.")
    return _compact(api_entry)


@mcp.tool()
def create_destination(name: str, type: str, options: dict, tags: Optional[list[str]] = None) -> str:
    """Create a notification destination.

    Call get_destination_type(type) first for required options and template examples.
    Common types: webhook (url), discord_webhook (url), slack (url), email, microsoft_teams_webhook (url, message_template).
    """
    _ensure_writable()
    body = _merge_body(name=name, type=type, options=options, tags=tags)
    return _compact(_request("POST", "/api/destinations", body=body))


@mcp.tool()
def update_destination(
    destination_id: int,
    name: Optional[str] = None,
    type: Optional[str] = None,
    options: Optional[dict] = None,
    tags: Optional[list[str]] = None,
) -> str:
    """Update a notification destination. When changing type, pass both type and options together."""
    _ensure_writable()
    body = _merge_body(name=name, type=type, options=options, tags=tags)
    return _compact(_request("POST", f"/api/destinations/{destination_id}", body=body))


# ---------------------------------------------------------------------------
# Visualizations and dashboard widgets
# ---------------------------------------------------------------------------


@mcp.tool()
def create_visualization(
    query_id: int,
    type: str,
    name: str,
    options: Optional[dict] = None,
    description: Optional[str] = None,
) -> str:
    """Add a visualization to a query. Common ``type`` values: TABLE, CHART, COUNTER, DETAILS."""
    _ensure_writable()
    body = _merge_body(
        query_id=query_id,
        type=type,
        name=name,
        options=options or {},
        description=description,
    )
    return _compact(_request("POST", "/api/visualizations", body=body))


@mcp.tool()
def update_visualization(
    visualization_id: int,
    name: Optional[str] = None,
    type: Optional[str] = None,
    options: Optional[dict] = None,
    description: Optional[str] = None,
) -> str:
    """Update a visualization on a query."""
    _ensure_writable()
    body = _merge_body(name=name, type=type, options=options, description=description)
    return _compact(_request("POST", f"/api/visualizations/{visualization_id}", body=body))


@mcp.tool()
def delete_visualization(visualization_id: int) -> str:
    """Delete a visualization from a query."""
    _ensure_writable()
    _request("DELETE", f"/api/visualizations/{visualization_id}")
    return _compact({"deleted": True, "visualization_id": visualization_id})


@mcp.tool()
def add_widget_to_dashboard(
    dashboard_id: int,
    visualization_id: Optional[int] = None,
    text: Optional[str] = None,
    options: Optional[dict] = None,
    width: int = 1,
) -> str:
    """Add a widget to a dashboard. Pass ``visualization_id`` for a chart/table, or ``text`` for a text box."""
    _ensure_writable()
    _require_widget_content(visualization_id, text)
    body = _merge_body(
        dashboard_id=dashboard_id,
        visualization_id=visualization_id,
        text=text,
        options=options or {},
        width=width,
    )
    return _compact(_request("POST", "/api/widgets", body=body))


@mcp.tool()
def update_widget(widget_id: int, text: Optional[str] = None, options: Optional[dict] = None) -> str:
    """Update a dashboard widget. Pass ``text`` and/or ``options`` (e.g. position/size in the layout grid)."""
    _ensure_writable()
    body = _merge_body(text=text, options=options)
    if not body:
        raise RuntimeError("Provide text and/or options to update a widget.")
    return _compact(_request("POST", f"/api/widgets/{widget_id}", body=body))


@mcp.tool()
def delete_widget(widget_id: int) -> str:
    """Remove a widget from a dashboard."""
    _ensure_writable()
    _request("DELETE", f"/api/widgets/{widget_id}")
    return _compact({"deleted": True, "widget_id": widget_id})


# ---------------------------------------------------------------------------
# Indexers (Rewatch extension)
# ---------------------------------------------------------------------------


@mcp.tool()
def list_indexers() -> str:
    """List indexers (Rewatch extension): ingestion jobs that materialize external data."""
    return _compact(_request("GET", "/api/indexers"))


@mcp.tool()
def create_indexer(
    name: str,
    query_id: int,
    data_source_id: int,
    options: Optional[dict] = None,
    tags: Optional[list[str]] = None,
) -> str:
    """Create an indexer that runs a query and writes results to a target data source."""
    _ensure_writable()
    body = _merge_body(
        name=name,
        query_id=query_id,
        data_source_id=data_source_id,
        options=options,
        tags=tags,
    )
    return _compact(_request("POST", "/api/indexers", body=body))


@mcp.tool()
def update_indexer(
    indexer_id: int,
    name: Optional[str] = None,
    query_id: Optional[int] = None,
    data_source_id: Optional[int] = None,
    options: Optional[dict] = None,
    tags: Optional[list[str]] = None,
) -> str:
    """Update an indexer definition."""
    _ensure_writable()
    body = _merge_body(
        name=name,
        query_id=query_id,
        data_source_id=data_source_id,
        options=options,
        tags=tags,
    )
    return _compact(_request("POST", f"/api/indexers/{indexer_id}", body=body))


def main() -> None:
    mcp.run()


if __name__ == "__main__":
    main()
