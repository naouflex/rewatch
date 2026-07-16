"""FastMCP stdio server exposing the Rewatch (Rewatch) REST API.

Design: three *meta* tools (``list_endpoints`` / ``describe_endpoint`` /
``call_api``) give full coverage of every route in the live OpenAPI spec
served at ``/api/spec``, and a handful of curated tools wrap the workflows
agents use most (running queries, browsing schemas, dashboards, alerts,
ML models).

Configuration (environment variables):

* ``REWATCH_BASE_URL``      — base URL of the instance (default ``http://localhost:5001``)
* ``REWATCH_API_KEY``       — required; user API key from the Rewatch UI
* ``REWATCH_MCP_READ_ONLY`` — when truthy, all mutating tools are disabled,
  ``call_api`` rejects non-GET methods, and ad-hoc ``query_text`` execution is
  rejected. Saved queries can still be executed (equivalent to viewing them in
  the UI), so data sources whose credentials permit writes are only as safe as
  their saved queries.
"""

from __future__ import annotations

import json
import os
import re
import sys
import time
from pathlib import Path
from typing import Any, Optional

import httpx
from dotenv import load_dotenv
from mcp.server.fastmcp import FastMCP

_WORKSPACE_ROOT = Path(__file__).resolve().parents[2]
if str(_WORKSPACE_ROOT) not in sys.path:
    sys.path.insert(0, str(_WORKSPACE_ROOT))


def _ensure_rewatch_importable() -> None:
    """Make ``rewatch.assistant.*`` importable without the Flask app.

    ``rewatch/__init__.py`` imports Flask and friends, which are not installed
    in the MCP server's own environment. The assistant helper modules
    (dashboard_builder, dashboard_layout, visualization_helpers) are
    dependency-free, so register stub package entries that let Python locate
    the submodules without executing the package __init__.
    """
    if "rewatch" in sys.modules:
        return
    try:
        import rewatch  # noqa: F401  (full package when server deps are installed)
    except Exception:
        import types

        stub = types.ModuleType("rewatch")
        stub.__path__ = [str(_WORKSPACE_ROOT / "rewatch")]
        sys.modules["rewatch"] = stub


_ensure_rewatch_importable()

try:
    from rewatch.assistant.visualization_helpers import (
        build_visualization_hints,
        enrich_visualizations_for_assistant,
        normalize_visualization_options,
        suggest_visualization_options,
    )
except ImportError:
    build_visualization_hints = None  # type: ignore[assignment,misc]
    enrich_visualizations_for_assistant = None  # type: ignore[assignment,misc]
    normalize_visualization_options = None  # type: ignore[assignment,misc]
    suggest_visualization_options = None  # type: ignore[assignment,misc]

try:
    from rewatch.assistant import dashboard_builder
except ImportError:
    dashboard_builder = None  # type: ignore[assignment]

try:
    from rewatch.assistant.dashboard_layout import (
        enrich_dashboard_for_assistant,
        find_invalid_widget_positions,
        has_explicit_position,
        normalize_widget_options,
        prepare_widget_options,
        prepare_widget_options_for_update,
        suggest_next_position,
        summarize_dashboard_layout,
    )
except ImportError:
    enrich_dashboard_for_assistant = None  # type: ignore[assignment,misc]
    find_invalid_widget_positions = None  # type: ignore[assignment,misc]
    has_explicit_position = None  # type: ignore[assignment,misc]
    normalize_widget_options = None  # type: ignore[assignment,misc]
    prepare_widget_options = None  # type: ignore[assignment,misc]
    prepare_widget_options_for_update = None  # type: ignore[assignment,misc]
    suggest_next_position = None  # type: ignore[assignment,misc]
    summarize_dashboard_layout = None  # type: ignore[assignment,misc]

try:
    from rewatch.assistant.datasources import enrich_data_sources
except ImportError:
    enrich_data_sources = None  # type: ignore[assignment,misc]

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
        "and call any REST API endpoint. For dashboards with 3+ widgets, prefer "
        "build_dashboard_from_spec — it validates, creates, lays out, and publishes "
        "everything in one call (use `derived` + {{cached_query.KEY}} for queries that "
        "aggregate other queries' cached results). Widget layout: add_widget_to_dashboard "
        "and update_widget always coerce col/row/sizeX/sizeY to numbers; get_dashboard "
        "reports layout_issues; repair_dashboard_layout fixes broken grids. For alerts: "
        "run_query first to validate columns, get_destination_type for webhook template "
        "examples, create_destination, then create_alert with destination_ids to subscribe. "
        "Use list_endpoints/describe_endpoint to discover the full API surface, then "
        "call_api for anything not covered by a dedicated tool (widget POSTs are still "
        "layout-normalized)."
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
    try:
        resp = _http().request(method.upper(), path, params=params, json=body)
    except httpx.HTTPError as exc:
        raise RuntimeError(f"{method.upper()} {path} against {BASE_URL} failed: {exc}") from exc
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


_MAX_OUTPUT_CHARS = 200_000


def _compact(obj: Any) -> str:
    text = json.dumps(obj, indent=2, default=str)
    if len(text) > _MAX_OUTPUT_CHARS:
        return (
            text[:_MAX_OUTPUT_CHARS]
            + f"\n… [truncated: response was {len(text)} characters; "
            "narrow the request (page_size, max_rows, filters) to see the rest]"
        )
    return text


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


def _require_layout_helpers() -> None:
    if prepare_widget_options is None or normalize_widget_options is None:
        raise RuntimeError(
            "Dashboard layout helpers are unavailable in this MCP environment. "
            "Cannot safely add or update widgets without position normalization."
        )


def _visualization_type(visualization_id: Optional[int]) -> Optional[str]:
    if not visualization_id:
        return None
    try:
        viz = _request("GET", f"/api/visualizations/{visualization_id}")
        return viz.get("type") if isinstance(viz, dict) else None
    except RuntimeError:
        return None


def _widget_visualization_type(widget: dict[str, Any]) -> Optional[str]:
    vis = widget.get("visualization") if isinstance(widget.get("visualization"), dict) else {}
    return vis.get("type")


def _prepare_widget_options_for_dashboard(
    dashboard_id: int,
    *,
    visualization_id: Optional[int] = None,
    text: Optional[str] = None,
    options: Optional[dict] = None,
    widget: Optional[dict[str, Any]] = None,
) -> dict[str, Any]:
    """Always return options.position with numeric col/row/sizeX/sizeY."""
    _require_layout_helpers()
    viz_type = _visualization_type(visualization_id) if visualization_id else None
    if widget and not viz_type:
        viz_type = _widget_visualization_type(widget)
    dashboard = _request("GET", f"/api/dashboards/{dashboard_id}")
    widgets = dashboard.get("widgets") if isinstance(dashboard.get("widgets"), list) else []
    if widget:
        return prepare_widget_options_for_update(  # type: ignore[misc]
            widget,
            widgets,
            visualization_type=viz_type,
            text=text,
            options=options,
        )
    return prepare_widget_options(  # type: ignore[misc]
        widgets,
        visualization_type=viz_type,
        text=text,
        options=options,
    )


def _normalize_widget_call_body(
    method: str,
    path: str,
    body: Optional[dict[str, Any]],
) -> Optional[dict[str, Any]]:
    """Coerce widget layout fields when agents use call_api instead of dedicated tools."""
    if not body or method.upper() != "POST":
        return body
    if prepare_widget_options is None or normalize_widget_options is None:
        return body

    if path == "/api/widgets":
        dashboard_id = body.get("dashboard_id")
        if not dashboard_id:
            return body
        body = dict(body)
        body["options"] = _prepare_widget_options_for_dashboard(
            int(dashboard_id),
            visualization_id=body.get("visualization_id"),
            text=body.get("text"),
            options=body.get("options"),
        )
        return body

    match = re.fullmatch(r"/api/widgets/(\d+)", path)
    if match and "options" in body:
        widget_id = int(match.group(1))
        widget = _request("GET", f"/api/widgets/{widget_id}")
        dashboard_id = widget.get("dashboard_id") if isinstance(widget, dict) else None
        if not dashboard_id:
            return body
        body = dict(body)
        body["options"] = _prepare_widget_options_for_dashboard(
            int(dashboard_id),
            text=body.get("text") or (widget.get("text") if isinstance(widget, dict) else None),
            options=body.get("options"),
            widget=widget if isinstance(widget, dict) else None,
        )
    return body


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
    body = _normalize_widget_call_body(method, path, body)
    return _compact(_request(method, path, params=query_params, body=body))


# ---------------------------------------------------------------------------
# Query execution
# ---------------------------------------------------------------------------


def _poll_job(job: dict, timeout_seconds: int) -> int:
    """Poll a background job until it finishes; return the query result id.

    Delegates to the shared, hardened implementation in
    ``rewatch.assistant.dashboard_builder`` (guards against string ``"None"``
    result ids and malformed job payloads) so the two poll loops cannot drift.
    """
    deadline = time.monotonic() + timeout_seconds
    if dashboard_builder is not None:
        try:
            return dashboard_builder._poll_job(_request, dict(job), deadline)
        except dashboard_builder.DashboardBuildError as exc:
            raise RuntimeError(str(exc)) from exc

    # Fallback when the shared module is unavailable in this install.
    job_id = job.get("id")
    if not job_id:
        raise RuntimeError(f"Job payload has no id: {job}")
    while True:
        status = job.get("status")
        if status == JOB_FINISHED:
            result_id = job.get("query_result_id") or job.get("result")
            if not result_id or result_id == "None":
                raise RuntimeError(f"Job {job_id} finished but returned no query result id: {job}")
            return int(result_id)
        if status in (JOB_FAILED, JOB_CANCELED):
            raise RuntimeError(f"Query execution failed: {job.get('error') or job}")
        if time.monotonic() >= deadline:
            raise RuntimeError(
                f"Query did not finish within {timeout_seconds}s (job {job_id} status {job.get('status')})."
            )
        time.sleep(1)
        response = _request("GET", f"/api/jobs/{job_id}")
        job = response.get("job") if isinstance(response, dict) and "job" in response else response
        if not isinstance(job, dict):
            raise RuntimeError(f"Unexpected job status payload: {job}")


def _run_query_internal(
    *,
    query_id: Optional[int] = None,
    query_text: Optional[str] = None,
    data_source_id: Optional[int] = None,
    parameters: Optional[dict] = None,
    max_age: int = -1,
    max_rows: int = 100,
    timeout_seconds: int = 120,
) -> dict[str, Any]:
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
    data = query_result.get("data", {})
    rows = data.get("rows", [])
    columns = [c.get("name") for c in data.get("columns", [])]
    result = {
        "query_result_id": query_result.get("id"),
        "retrieved_at": query_result.get("retrieved_at"),
        "runtime_seconds": query_result.get("runtime"),
        "columns": columns,
        "row_count": len(rows),
        "rows": rows[:max_rows],
    }
    if build_visualization_hints is not None:
        result["visualization_hints"] = build_visualization_hints(columns, rows)
    if len(rows) > max_rows:
        result["note"] = f"Showing first {max_rows} of {len(rows)} rows."
    return result


def _execute_saved_query_validation(
    query_id: int,
    parameters: Optional[dict] = None,
    max_rows: int = 10,
    max_age: int = 0,
) -> dict[str, Any]:
    try:
        result = _run_query_internal(
            query_id=query_id,
            parameters=parameters,
            max_age=max_age,
            max_rows=max_rows,
            timeout_seconds=120,
        )
        return {"status": "ok", "message": f"Query ran successfully ({result.get('row_count', 0)} rows returned).", **result}
    except RuntimeError as exc:
        message = str(exc)
        if "Missing parameter" in message:
            return {"status": "needs_parameters", "message": message}
        return {"status": "error", "message": message}


def _normalize_viz_options_or_raise(
    viz_type: str,
    options: Optional[dict],
    columns: list[str],
    rows: list[dict[str, Any]],
) -> tuple[dict[str, Any], list[str]]:
    if normalize_visualization_options is None:
        return dict(options or {}), []
    return normalize_visualization_options(viz_type, options, columns, rows)


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
    if READ_ONLY and query_text is not None:
        raise RuntimeError(
            "This MCP server is running in read-only mode (REWATCH_MCP_READ_ONLY); "
            "ad-hoc query_text execution is disabled. Pass query_id to run a saved query."
        )
    return _compact(
        _run_query_internal(
            query_id=query_id,
            query_text=query_text,
            data_source_id=data_source_id,
            parameters=parameters,
            max_age=max_age,
            max_rows=max_rows,
            timeout_seconds=timeout_seconds,
        )
    )


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
    """Get a saved query: its SQL text, data source, parameters, schedule and visualizations.

    Also fetches query results (cached when available, executing only if no
    cache exists) and returns validation columns, visualization_hints, and
    per-visualization options_health when column mappings are broken. Use
    run_query(query_id, max_age=0) to force a fresh execution.
    """
    query = _request("GET", f"/api/queries/{query_id}")
    if READ_ONLY:
        query["validation"] = {
            "status": "skipped",
            "message": "Query execution skipped in read-only mode (REWATCH_MCP_READ_ONLY).",
        }
        return _compact(query)
    validation = _execute_saved_query_validation(query_id, max_age=-1)
    query["validation"] = validation
    if validation.get("status") == "ok" and enrich_visualizations_for_assistant is not None:
        columns = validation.get("columns") or []
        rows = validation.get("rows") or []
        query["visualization_hints"] = validation.get("visualization_hints") or build_visualization_hints(columns, rows)
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
                "query_id": query_id,
                "broken_visualization_ids": [viz.get("id") for viz in unhealthy if viz.get("id")],
            }
    return _compact(query)


def _test_query_text_before_save(query: str, data_source_id: int) -> dict[str, Any]:
    try:
        result = _run_query_internal(
            query_text=query,
            data_source_id=data_source_id,
            max_age=0,
            max_rows=10,
            timeout_seconds=120,
        )
        return {
            "status": "ok",
            "phase": "pre_save",
            "message": f"Query test passed ({result.get('row_count', 0)} rows returned).",
            **result,
        }
    except RuntimeError as exc:
        message = str(exc)
        if "Missing parameter" in message:
            return {"status": "needs_parameters", "phase": "pre_save", "message": message}
        return {"status": "error", "phase": "pre_save", "message": message}


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

    ``query`` is the query text (syntax depends on the data source type — call
    get_query_runner_type first for non-SQL sources). ``data_source_id`` comes
    from list_data_sources. The query text is executed automatically before
    saving; read the ``validation`` block in the response and fix errors
    with update_query instead of creating duplicates.
    ``schedule`` example: ``{"interval": 3600, "time": null, "day_of_week": null, "until": null}``.
    """
    _ensure_writable()
    pre_validation = _test_query_text_before_save(query, data_source_id)
    if pre_validation.get("status") == "error":
        raise RuntimeError(f"Query failed validation before save: {pre_validation['message']}")
    body = _merge_body(
        name=name,
        query=query,
        data_source_id=data_source_id,
        description=description,
        schedule=schedule,
        options=options,
        tags=tags,
    )
    saved = _request("POST", "/api/queries", body=body)
    if isinstance(saved, dict):
        # The query text was executed just before saving; re-running it here
        # would double the cost (and API quota for external-API data sources).
        saved["validation"] = {"pre_save": pre_validation}
    return _compact(saved)


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
    """Update a saved query. Fetches the current version automatically unless you pass one.

    When ``query`` text changes it is executed before and after saving; read the
    ``validation`` block in the response.
    """
    _ensure_writable()
    current = _request("GET", f"/api/queries/{query_id}")
    pre_validation: Optional[dict[str, Any]] = None
    if query is not None:
        effective_ds = data_source_id or current.get("data_source_id")
        pre_validation = _test_query_text_before_save(query, effective_ds)
        if pre_validation.get("status") == "error":
            raise RuntimeError(f"Query failed validation before save: {pre_validation['message']}")
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
    saved = _request("POST", f"/api/queries/{query_id}", body=body)
    if query is not None and isinstance(saved, dict):
        post_save = _execute_saved_query_validation(query_id)
        validation: dict[str, Any] = {"post_save": post_save}
        if pre_validation is not None:
            validation["pre_save"] = pre_validation
        if post_save.get("status") == "error":
            validation["action_required"] = (
                f"Query #{query_id} was updated but failed to run. Fix it with update_query."
            )
        saved["validation"] = validation
    return _compact(saved)


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
    """List connected data sources (id, name, type) with query_runner syntax summaries.

    Always call before create_query when the data source is unknown; each entry
    includes query syntax hints and example queries for its runner type.
    """
    payload = _request("GET", "/api/data_sources")
    if enrich_data_sources is not None:
        payload = enrich_data_sources(payload)
    return _compact(payload)


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
    """Get a dashboard with its widgets and the queries/visualizations they reference.

    Includes ``layout_summary`` (widget ids, grid positions, placement hints).
    Always call before rearranging widgets on an existing dashboard.
    """
    dashboard = _request("GET", f"/api/dashboards/{dashboard_id}")
    if enrich_dashboard_for_assistant is not None and isinstance(dashboard, dict):
        dashboard = enrich_dashboard_for_assistant(dashboard)
    return _compact(dashboard)


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


def _subscribe_alert_destinations(
    alert_id: int, destination_ids: list[int]
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Subscribe destinations one by one; a failure must not lose the created alert."""
    subscriptions: list[dict[str, Any]] = []
    errors: list[dict[str, Any]] = []
    for destination_id in destination_ids:
        try:
            subscriptions.append(
                _request("POST", f"/api/alerts/{alert_id}/subscriptions", body={"destination_id": destination_id})
            )
        except RuntimeError as exc:
            errors.append({"destination_id": destination_id, "error": str(exc)})
    return subscriptions, errors


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
        subscriptions, subscription_errors = _subscribe_alert_destinations(alert["id"], destination_ids)
        result["subscriptions"] = subscriptions
        if subscription_errors:
            result["subscription_errors"] = subscription_errors
            result["note"] = (
                f"Alert #{alert['id']} was created but {len(subscription_errors)} destination "
                "subscription(s) failed — retry them with subscribe_alert (do NOT create a new alert)."
            )
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
    """Update an alert's name, linked query, trigger options (incl. custom_body/custom_subject), rearm or tags.

    Partial ``options`` are merged into the alert's existing options (the API
    replaces the options column wholesale, so e.g. ``{"muted": true}`` alone
    would otherwise destroy the trigger condition). The merged result is
    validated before saving.
    """
    _ensure_writable()
    if options is not None:
        current = _request("GET", f"/api/alerts/{alert_id}")
        current_options = current.get("options") if isinstance(current.get("options"), dict) else {}
        options = {**current_options, **options}
        if alert_catalog is not None:
            try:
                alert_catalog.validate_alert_operator(options.get("op"))
                alert_catalog.validate_alert_selector_value(options.get("selector") or "first")
            except ValueError as exc:
                raise RuntimeError(str(exc)) from exc
        if not options.get("column"):
            raise RuntimeError(
                "Merged alert options have no trigger column. Pass options with at least "
                "column/op/value, or fix the alert's existing options first."
            )
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
    """Add a visualization to a query. Common ``type`` values: TABLE, CHART, COUNTER, DETAILS.

    For CHART/COUNTER/MAP/CHOROPLETH, omit options to auto-map columns from query results.
    Invalid column names in options are corrected automatically.
    """
    _ensure_writable()
    validation = _execute_saved_query_validation(query_id)
    if validation.get("status") != "ok":
        raise RuntimeError(f"Cannot create visualization: {validation.get('message', validation)}")

    viz_type = (type or "").upper()
    columns = validation.get("columns") or []
    rows = validation.get("rows") or []
    user_options = options
    if not user_options and suggest_visualization_options is not None:
        resolved_options, corrections = _normalize_viz_options_or_raise(
            viz_type,
            suggest_visualization_options(viz_type, columns, rows),
            columns,
            rows,
        )
    else:
        resolved_options, corrections = _normalize_viz_options_or_raise(viz_type, user_options, columns, rows)

    body = _merge_body(
        query_id=query_id,
        type=type,
        name=name,
        options=resolved_options or {},
        description=description,
    )
    result = _request("POST", "/api/visualizations", body=body)
    if corrections:
        result["column_corrections"] = corrections
    result["query_validation"] = validation
    return _compact(result)


@mcp.tool()
def update_visualization(
    visualization_id: int,
    name: Optional[str] = None,
    type: Optional[str] = None,
    options: Optional[dict] = None,
    description: Optional[str] = None,
    remap_columns: bool = True,
) -> str:
    """Update a visualization on a query.

    When ``remap_columns`` is true (default), re-validates the parent query and auto-corrects
    column mappings in options against live query results.
    """
    _ensure_writable()
    current = _request("GET", f"/api/visualizations/{visualization_id}")
    query_id = current.get("query_id")
    corrections: list[str] = []
    validation: Optional[dict[str, Any]] = None
    resolved_options = options

    if remap_columns and query_id:
        validation = _execute_saved_query_validation(query_id)
        if validation.get("status") != "ok":
            raise RuntimeError(f"Cannot update visualization: {validation.get('message', validation)}")
        viz_type = (type or current.get("type") or "").upper()
        current_options = current.get("options") if isinstance(current.get("options"), dict) else {}
        merged_options = {**current_options, **(options or {})}
        resolved_options, corrections = _normalize_viz_options_or_raise(
            viz_type,
            merged_options,
            validation.get("columns") or [],
            validation.get("rows") or [],
        )

    body = _merge_body(name=name, type=type, options=resolved_options, description=description)
    result = _request("POST", f"/api/visualizations/{visualization_id}", body=body)
    if corrections:
        result["column_corrections"] = corrections
    if validation:
        result["query_validation"] = validation
    return _compact(result)


@mcp.tool()
def fix_query_visualizations(query_id: int) -> str:
    """Fix all visualizations on a query by auto-correcting column mappings from live query results."""
    _ensure_writable()
    query = _request("GET", f"/api/queries/{query_id}")
    validation = _execute_saved_query_validation(query_id)
    if validation.get("status") != "ok":
        raise RuntimeError(f"Cannot fix visualizations: {validation.get('message', validation)}")

    columns = validation.get("columns") or []
    rows = validation.get("rows") or []
    fixed = []
    skipped = []
    for visualization in query.get("visualizations") or []:
        if not isinstance(visualization, dict):
            continue
        viz_id = visualization.get("id")
        viz_type = (visualization.get("type") or "").upper()
        if not viz_id or viz_type in {"TABLE", "DETAILS"}:
            skipped.append({"id": viz_id, "name": visualization.get("name"), "reason": "no column mapping"})
            continue
        current_options = visualization.get("options") if isinstance(visualization.get("options"), dict) else {}
        resolved_options, corrections = _normalize_viz_options_or_raise(viz_type, current_options, columns, rows)
        updated = _request(
            "POST",
            f"/api/visualizations/{viz_id}",
            body={"name": visualization.get("name"), "options": resolved_options},
        )
        entry = {"id": viz_id, "name": updated.get("name"), "type": viz_type, "resolved_options": resolved_options}
        if corrections:
            entry["column_corrections"] = corrections
        fixed.append(entry)

    return _compact(
        {
            "query_id": query_id,
            "query_validation": validation,
            "fixed_count": len(fixed),
            "skipped_count": len(skipped),
            "fixed": fixed,
            "skipped": skipped,
        }
    )


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
    """Add a widget to a dashboard. Pass ``visualization_id`` for a chart/table, or ``text`` for a text box.

    Omit ``options`` to auto-place below existing widgets with a type-aware size
    (counters 3x3 packed side by side, charts 6x8, tables 12x8). Pass explicit
    ``options.position`` (col, row, sizeX, sizeY on a 12-column grid) to override.
    Positions are always normalized server-side — col/row/sizeX/sizeY must be numbers.
    """
    _ensure_writable()
    _require_widget_content(visualization_id, text)
    options = _prepare_widget_options_for_dashboard(
        dashboard_id,
        visualization_id=visualization_id,
        text=text,
        options=options,
    )
    body = _merge_body(
        dashboard_id=dashboard_id,
        visualization_id=visualization_id,
        text=text,
        options=options,
        width=width,
    )
    widget = _request("POST", "/api/widgets", body=body)
    if isinstance(widget, dict) and summarize_dashboard_layout is not None:
        dashboard = _request("GET", f"/api/dashboards/{dashboard_id}")
        widgets = dashboard.get("widgets") if isinstance(dashboard.get("widgets"), list) else []
        widget["layout_summary"] = summarize_dashboard_layout(widgets)
    return _compact(widget)


@mcp.tool()
def update_widget(widget_id: int, text: Optional[str] = None, options: Optional[dict] = None) -> str:
    """Update a dashboard widget. Pass ``text`` and/or ``options`` (e.g. position/size in the layout grid).

    When ``options`` includes ``position``, all of col, row, sizeX, and sizeY are coerced to numbers.
    """
    _ensure_writable()
    body = _merge_body(text=text)
    if options is not None:
        widget = _request("GET", f"/api/widgets/{widget_id}")
        dashboard_id = widget.get("dashboard_id") if isinstance(widget, dict) else None
        if not dashboard_id:
            raise RuntimeError(f"Widget {widget_id} has no dashboard_id.")
        body["options"] = _prepare_widget_options_for_dashboard(
            dashboard_id,
            text=text or (widget.get("text") if isinstance(widget, dict) else None),
            options=options,
            widget=widget if isinstance(widget, dict) else None,
        )
    if not body:
        raise RuntimeError("Provide text and/or options to update a widget.")
    return _compact(_request("POST", f"/api/widgets/{widget_id}", body=body))


@mcp.tool()
def delete_widget(widget_id: int) -> str:
    """Remove a widget from a dashboard."""
    _ensure_writable()
    _request("DELETE", f"/api/widgets/{widget_id}")
    return _compact({"deleted": True, "widget_id": widget_id})


@mcp.tool()
def repair_dashboard_layout(dashboard_id: int) -> str:
    """Fix widgets with null or invalid grid positions that would crash the dashboard UI.

    Coerces col, row, sizeX, and sizeY to numbers for every broken widget. Call
    ``get_dashboard`` first to inspect ``layout_summary.layout_issues``.
    """
    _ensure_writable()
    _require_layout_helpers()
    dashboard = _request("GET", f"/api/dashboards/{dashboard_id}")
    widgets = dashboard.get("widgets") if isinstance(dashboard.get("widgets"), list) else []
    issues = find_invalid_widget_positions(widgets)  # type: ignore[misc]
    if not issues:
        return _compact({"dashboard_id": dashboard_id, "repaired": 0, "message": "No layout issues found."})

    repaired: list[dict[str, Any]] = []
    for issue in issues:
        widget_id = issue.get("widget_id")
        if not widget_id:
            continue
        widget = next((w for w in widgets if isinstance(w, dict) and w.get("id") == widget_id), None)
        if not widget:
            continue
        options = normalize_widget_options(  # type: ignore[misc]
            {"position": issue.get("position") or {}},
            visualization_type=_widget_visualization_type(widget),
        )
        updated = _request("POST", f"/api/widgets/{widget_id}", body={"options": options})
        repaired.append(
            {
                "widget_id": widget_id,
                "position": options.get("position"),
                "visualization_name": issue.get("visualization_name"),
                "widget": updated if isinstance(updated, dict) else None,
            }
        )

    dashboard = _request("GET", f"/api/dashboards/{dashboard_id}")
    if enrich_dashboard_for_assistant is not None and isinstance(dashboard, dict):
        dashboard = enrich_dashboard_for_assistant(dashboard)
    return _compact(
        {
            "dashboard_id": dashboard_id,
            "repaired": len(repaired),
            "widgets": repaired,
            "layout_summary": dashboard.get("layout_summary") if isinstance(dashboard, dict) else None,
        }
    )


@mcp.tool()
def build_dashboard_from_spec(
    name: str,
    queries: list[dict],
    widgets: list[dict],
    derived: Optional[list[dict]] = None,
    publish: bool = True,
    validate_before_create: bool = True,
) -> str:
    """Build a complete dashboard in ONE call: validate, create, and publish all
    queries, visualizations, and widgets from a declarative spec.

    PREFER THIS over separate create_query / create_visualization /
    add_widget_to_dashboard calls whenever a dashboard needs 3+ widgets. Every
    query is executed for validation first — nothing is created if any fails.

    ``queries``: [{key?, name, description?, data_source_id, query,
    visualizations: [{type, name, chart_type?, column_mapping?, counter_column?,
    counter_label?, options?}]}]. Give a query a ``key`` so derived queries can
    reference its cached results.

    ``derived``: second-phase queries on the Query Results data source. Their
    query text may reference base queries as ``{{cached_query.KEY}}``
    placeholders, resolved after base queries are created and refreshed.
    Derived SQL runs on SQLite — no PostgreSQL casts like ``::numeric``.

    ``widgets``: ordered [{visualization: "<viz name>"} or {text: "markdown"}],
    each with optional {position: {col,row,sizeX,sizeY}} or {role: "title" |
    "section" | "kpi" | "half" | "third" | "full"}. Widgets without explicit
    positions are packed onto a 12-column grid with type-aware sizes (counters
    3x3 four per row, charts 6x8, tables 12x8, text headers full width).

    Set ``validate_before_create=false`` for expensive external-API queries
    that should run only once (create → refresh → derived) to avoid doubling
    rate-limited API quota usage.
    """
    _ensure_writable()
    if dashboard_builder is None:
        raise RuntimeError("dashboard_builder is unavailable in this MCP install.")
    try:
        result = dashboard_builder.build_dashboard_from_spec(
            _request,
            name=name,
            queries=queries,
            widgets=widgets,
            derived=derived,
            publish=publish,
            validate_before_create=validate_before_create,
        )
    except dashboard_builder.DashboardBuildError as exc:
        raise RuntimeError(str(exc)) from exc
    return _compact(result)


@mcp.tool()
def refresh_queries_and_wait(query_ids: list[int], timeout_seconds: int = 180) -> str:
    """Refresh saved queries and wait until their cached results are stored.

    Required before creating queries on the Query Results data source that read
    ``cached_query_{id}`` tables.
    """
    _ensure_writable()
    if dashboard_builder is None:
        raise RuntimeError("dashboard_builder is unavailable in this MCP install.")
    return _compact(
        dashboard_builder.refresh_queries_and_wait(_request, query_ids, timeout_seconds=timeout_seconds)
    )


@mcp.tool()
def create_multi_visualization_query(
    name: str,
    query: str,
    data_source_id: int,
    visualizations: list[dict],
    description: Optional[str] = None,
) -> str:
    """Create one query plus several visualizations in a single call.

    Ideal for a wide summary row rendered as multiple KPI counters. The query
    text is validated by execution first; visualization column names are checked
    against real result columns. The query is published on success.

    ``visualizations``: [{type, name, chart_type?, column_mapping?,
    counter_column?, counter_label?, options?}].
    """
    _ensure_writable()
    if dashboard_builder is None:
        raise RuntimeError("dashboard_builder is unavailable in this MCP install.")
    try:
        result = dashboard_builder.create_query_with_visualizations(
            _request,
            name=name,
            query=query,
            data_source_id=data_source_id,
            visualizations=visualizations,
            description=description,
        )
    except dashboard_builder.DashboardBuildError as exc:
        raise RuntimeError(str(exc)) from exc
    return _compact(result)


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
