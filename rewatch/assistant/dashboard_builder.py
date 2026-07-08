"""Composite dashboard builder: validate, create, refresh, and lay out in one pass.

This module encodes the "script-style" pipeline that produces polished
dashboards reliably:

1. Validate every query against its data source (columns + sample rows).
2. Create queries and publish them (``is_draft=false``); create all
   visualizations per query with column-validated options.
3. Refresh base queries so ``cached_query_{id}`` tables exist, then create
   derived queries on the Query Results data source (two-phase builds).
4. Create the dashboard, place widgets on a curated 12-column grid, publish.

It is transport-agnostic: every function takes a ``request`` callable with the
signature ``request(method, path, *, params=None, body=None) -> Any`` so the
same code serves the in-app assistant (``ToolContext.request``) and the MCP
server (``_request``). It must stay importable without Flask.
"""

from __future__ import annotations

import re
import time
from typing import Any, Callable, Optional

from rewatch.assistant.dashboard_layout import (
    normalize_widget_options,
    plan_dashboard_layout,
    summarize_dashboard_layout,
)
from rewatch.assistant.visualization_helpers import (
    normalize_visualization_options,
    suggest_chart_options,
    suggest_visualization_options,
)

RequestFn = Callable[..., Any]

JOB_FINISHED = 3
JOB_FAILED = 4
JOB_CANCELED = 5

_CACHED_QUERY_PLACEHOLDER = re.compile(r"\{\{\s*cached_query\.([A-Za-z0-9_\-]+)\s*\}\}")


class DashboardBuildError(RuntimeError):
    """Raised when a build cannot proceed (validation failures, timeouts)."""


# ---------------------------------------------------------------------------
# Query execution helpers
# ---------------------------------------------------------------------------


def _poll_job(request: RequestFn, job: dict[str, Any], deadline: float) -> int:
    job_id = job.get("id")
    if not job_id:
        raise DashboardBuildError(f"Job payload has no id: {job}")
    while time.monotonic() < deadline:
        status = job.get("status")
        if status == JOB_FINISHED:
            result_id = job.get("query_result_id") or job.get("result")
            if not result_id or result_id == "None":
                raise DashboardBuildError(f"Job {job_id} finished without a query result id.")
            return int(result_id)
        if status in (JOB_FAILED, JOB_CANCELED):
            raise DashboardBuildError(str(job.get("error") or "Query execution failed"))
        time.sleep(1)
        response = request("GET", f"/api/jobs/{job_id}")
        job = response.get("job") if isinstance(response, dict) and "job" in response else response
        if not isinstance(job, dict):
            raise DashboardBuildError(f"Unexpected job status payload: {job}")
    raise DashboardBuildError(f"Query timed out (job {job_id}).")


def _extract_result(response: Any) -> tuple[list[str], list[dict[str, Any]]]:
    query_result = response.get("query_result", response) if isinstance(response, dict) else {}
    data = query_result.get("data") if isinstance(query_result, dict) else {}
    data = data if isinstance(data, dict) else {}
    columns = [c.get("name") for c in data.get("columns", []) if isinstance(c, dict) and c.get("name")]
    rows = [row for row in data.get("rows", []) if isinstance(row, dict)]
    return columns, rows


def run_adhoc_query(
    request: RequestFn,
    query_text: str,
    data_source_id: int,
    *,
    timeout_seconds: int = 120,
) -> tuple[list[str], list[dict[str, Any]]]:
    """Execute query text and return (columns, rows). Raises on failure."""
    deadline = time.monotonic() + timeout_seconds
    response = request(
        "POST",
        "/api/query_results",
        body={
            "query": query_text,
            "data_source_id": data_source_id,
            "max_age": 0,
            "parameters": {},
            "apply_auto_limit": True,
        },
    )
    if isinstance(response, dict) and "job" in response:
        result_id = _poll_job(request, dict(response["job"]), deadline)
        response = request("GET", f"/api/query_results/{result_id}")
    return _extract_result(response)


def refresh_queries_and_wait(
    request: RequestFn,
    query_ids: list[int],
    *,
    timeout_seconds: int = 180,
) -> dict[str, Any]:
    """Refresh saved queries and wait until their cached results are stored.

    Required before creating derived queries that read ``cached_query_{id}``
    tables on the Query Results data source.
    """
    deadline = time.monotonic() + timeout_seconds
    refreshed: list[dict[str, Any]] = []
    failures: list[dict[str, Any]] = []
    for query_id in query_ids:
        try:
            response = request("POST", f"/api/queries/{query_id}/refresh")
            job = response.get("job") if isinstance(response, dict) else None
            if isinstance(job, dict):
                _poll_job(request, dict(job), deadline)
            refreshed.append({"query_id": query_id, "status": "ok"})
        except (RuntimeError, DashboardBuildError) as exc:
            failures.append({"query_id": query_id, "status": "error", "message": str(exc)})
    return {
        "refreshed": refreshed,
        "failures": failures,
        "note": (
            "Cached results are now available as cached_query_{id} tables on the "
            "Query Results data source." if not failures else
            "Some refreshes failed — fix those queries before referencing their cached_query_{id} tables."
        ),
    }


# ---------------------------------------------------------------------------
# Visualization option resolution
# ---------------------------------------------------------------------------


def resolve_visualization_spec(
    viz_spec: dict[str, Any],
    columns: list[str],
    rows: list[dict[str, Any]],
) -> tuple[str, str, dict[str, Any], list[str]]:
    """Resolve one visualization spec into (type, name, options, corrections)."""
    viz_type = (viz_spec.get("type") or "TABLE").upper()
    name = viz_spec.get("name") or viz_type.title()

    if viz_type == "TABLE":
        return viz_type, name, dict(viz_spec.get("options") or {}), []

    options = dict(viz_spec.get("options") or {})
    if viz_type == "CHART" and not options:
        chart_type = viz_spec.get("chart_type") or viz_spec.get("chart")
        mapping = viz_spec.get("column_mapping") or viz_spec.get("mapping")
        options = suggest_chart_options(columns, rows, series_type=chart_type)
        if isinstance(mapping, dict) and mapping:
            options["columnMapping"] = dict(mapping)
    elif viz_type == "COUNTER" and not options:
        counter_column = viz_spec.get("counter_column")
        options = {
            "counterColName": counter_column or "",
            "counterLabel": viz_spec.get("counter_label") or "",
            "rowNumber": 1,
            "targetRowNumber": 1,
        }
    elif not options:
        options = suggest_visualization_options(viz_type, columns, rows)

    normalized, corrections = normalize_visualization_options(viz_type, options, columns, rows)
    return viz_type, name, normalized, corrections


# ---------------------------------------------------------------------------
# Query + visualization creation
# ---------------------------------------------------------------------------


def _publish_query(request: RequestFn, query: dict[str, Any]) -> None:
    request(
        "POST",
        f"/api/queries/{query['id']}",
        body={"is_draft": False, "version": query.get("version", 1)},
    )


def create_query_with_visualizations(
    request: RequestFn,
    *,
    name: str,
    query: str,
    data_source_id: int,
    visualizations: Optional[list[dict[str, Any]]] = None,
    description: Optional[str] = None,
    publish: bool = True,
    timeout_seconds: int = 120,
) -> dict[str, Any]:
    """Validate query text, save it, and create all its visualizations atomically.

    Returns {query_id, name, columns, row_count, visualizations: [...], corrections}.
    """
    columns, rows = run_adhoc_query(request, query, data_source_id, timeout_seconds=timeout_seconds)
    if not columns:
        raise DashboardBuildError(f"Query {name!r} returned no columns; fix the query text before saving.")

    body: dict[str, Any] = {
        "name": name,
        "query": query,
        "data_source_id": data_source_id,
    }
    if description:
        body["description"] = description
    saved = request("POST", "/api/queries", body=body)
    if not isinstance(saved, dict) or not saved.get("id"):
        raise DashboardBuildError(f"Failed to save query {name!r}: {saved}")
    query_id = saved["id"]
    if publish:
        _publish_query(request, saved)

    created_vizs: list[dict[str, Any]] = []
    all_corrections: list[str] = []
    for viz_spec in visualizations or []:
        viz_type, viz_name, options, corrections = resolve_visualization_spec(viz_spec, columns, rows)
        viz = request(
            "POST",
            "/api/visualizations",
            body={
                "query_id": query_id,
                "type": viz_type,
                "name": viz_name,
                "options": options,
                "description": viz_spec.get("description") or "",
            },
        )
        created_vizs.append(
            {
                "id": viz.get("id") if isinstance(viz, dict) else None,
                "name": viz_name,
                "type": viz_type,
                "query_id": query_id,
            }
        )
        all_corrections.extend(f"{viz_name}: {c}" for c in corrections)

    return {
        "query_id": query_id,
        "name": name,
        "columns": columns,
        "row_count": len(rows),
        "sample_row": rows[0] if rows else None,
        "visualizations": created_vizs,
        "corrections": all_corrections,
    }


# ---------------------------------------------------------------------------
# Full dashboard build
# ---------------------------------------------------------------------------


def _find_results_data_source_id(request: RequestFn) -> Optional[int]:
    sources = request("GET", "/api/data_sources")
    if isinstance(sources, dict):
        sources = sources.get("data_sources") or []
    for source in sources or []:
        if isinstance(source, dict) and (source.get("type") or "").lower() == "results":
            return source.get("id")
    return None


def _substitute_cached_query_refs(query_text: str, key_to_id: dict[str, int]) -> str:
    def repl(match: re.Match) -> str:
        key = match.group(1)
        if key not in key_to_id:
            raise DashboardBuildError(
                f"Derived query references unknown base query key {key!r}. "
                f"Known keys: {sorted(key_to_id)}"
            )
        return f"cached_query_{key_to_id[key]}"

    return _CACHED_QUERY_PLACEHOLDER.sub(repl, query_text)


def build_dashboard_from_spec(
    request: RequestFn,
    *,
    name: str,
    queries: list[dict[str, Any]],
    widgets: list[dict[str, Any]],
    derived: Optional[list[dict[str, Any]]] = None,
    publish: bool = True,
    results_data_source_id: Optional[int] = None,
    timeout_seconds: int = 300,
) -> dict[str, Any]:
    """Build a complete dashboard from a declarative spec in one call.

    ``queries``: [{key?, name, description?, data_source_id, query,
    visualizations: [{type, name, chart_type?, column_mapping?,
    counter_column?, counter_label?, options?}]}]. Every query is executed for
    validation before anything is created; visualization column mappings are
    checked against real result columns.

    ``derived``: same shape minus ``data_source_id`` (defaults to the Query
    Results source). Their ``query`` text may reference base queries with
    ``{{cached_query.KEY}}`` placeholders, which are replaced with the real
    ``cached_query_{id}`` table names after base queries are created and
    refreshed. Derived SQL runs on SQLite — avoid PostgreSQL-only syntax like
    ``::numeric`` casts.

    ``widgets``: ordered list of {visualization: "<viz name>"} or
    {text: "markdown"}, each with optional {position: {col,row,sizeX,sizeY}}
    or {role: "title"|"section"|"kpi"|"half"|"third"|"full"}. Widgets without
    explicit positions are packed onto the 12-column grid with type-aware
    sizes (counters 3x8 four-per-row, charts 6x8, tables 12x8).
    """
    deadline = time.monotonic() + timeout_seconds
    warnings: list[str] = []

    def remaining() -> int:
        return max(10, int(deadline - time.monotonic()))

    # Phase 0: validate every base query before creating anything.
    validated: list[dict[str, Any]] = []
    validation_errors: list[str] = []
    for query_spec in queries:
        query_name = query_spec.get("name") or "(unnamed)"
        data_source_id = query_spec.get("data_source_id")
        if not data_source_id:
            validation_errors.append(f"{query_name}: missing data_source_id.")
            continue
        try:
            columns, rows = run_adhoc_query(
                request, query_spec["query"], data_source_id, timeout_seconds=remaining()
            )
            if not columns:
                validation_errors.append(f"{query_name}: query returned no columns.")
                continue
            validated.append({**query_spec, "_columns": columns, "_rows": rows})
        except (RuntimeError, DashboardBuildError) as exc:
            validation_errors.append(f"{query_name}: {exc}")
    if validation_errors:
        raise DashboardBuildError(
            "Query validation failed — nothing was created. Fix these and retry:\n- "
            + "\n- ".join(validation_errors)
        )

    # Phase 1: create base queries + visualizations.
    viz_name_to_id: dict[str, int] = {}
    key_to_query_id: dict[str, int] = {}
    created_queries: list[dict[str, Any]] = []

    def create_from_spec(query_spec: dict[str, Any], columns: list[str], rows: list[dict[str, Any]]) -> None:
        body: dict[str, Any] = {
            "name": query_spec["name"],
            "query": query_spec["query"],
            "data_source_id": query_spec["data_source_id"],
        }
        if query_spec.get("description"):
            body["description"] = query_spec["description"]
        saved = request("POST", "/api/queries", body=body)
        if not isinstance(saved, dict) or not saved.get("id"):
            raise DashboardBuildError(f"Failed to save query {query_spec['name']!r}: {saved}")
        query_id = saved["id"]
        _publish_query(request, saved)
        if query_spec.get("key"):
            key_to_query_id[str(query_spec["key"])] = query_id

        viz_entries: list[dict[str, Any]] = []
        for viz_spec in query_spec.get("visualizations") or []:
            viz_type, viz_name, options, corrections = resolve_visualization_spec(viz_spec, columns, rows)
            viz = request(
                "POST",
                "/api/visualizations",
                body={
                    "query_id": query_id,
                    "type": viz_type,
                    "name": viz_name,
                    "options": options,
                    "description": viz_spec.get("description") or "",
                },
            )
            viz_id = viz.get("id") if isinstance(viz, dict) else None
            if viz_name in viz_name_to_id:
                warnings.append(
                    f"Duplicate visualization name {viz_name!r}; widgets referencing it use the latest one."
                )
            if viz_id:
                viz_name_to_id[viz_name] = viz_id
            viz_entries.append({"id": viz_id, "name": viz_name, "type": viz_type})
            warnings.extend(f"{viz_name}: {c}" for c in corrections)

        created_queries.append(
            {
                "key": query_spec.get("key"),
                "query_id": query_id,
                "name": query_spec["name"],
                "columns": columns,
                "row_count": len(rows),
                "visualizations": viz_entries,
            }
        )

    for query_spec in validated:
        create_from_spec(query_spec, query_spec.pop("_columns"), query_spec.pop("_rows"))

    # Phase 2: refresh base queries and create derived queries.
    if derived:
        base_ids = [entry["query_id"] for entry in created_queries]
        refresh_result = refresh_queries_and_wait(request, base_ids, timeout_seconds=remaining())
        for failure in refresh_result["failures"]:
            warnings.append(f"Refresh failed for query {failure['query_id']}: {failure['message']}")

        if results_data_source_id is None:
            results_data_source_id = _find_results_data_source_id(request)
        if results_data_source_id is None:
            raise DashboardBuildError(
                "Cannot create derived queries: no Query Results data source found. "
                "Pass results_data_source_id explicitly."
            )

        for derived_spec in derived:
            derived_name = derived_spec.get("name") or "(unnamed derived)"
            try:
                query_text = _substitute_cached_query_refs(derived_spec["query"], key_to_query_id)
                columns, rows = run_adhoc_query(
                    request, query_text, results_data_source_id, timeout_seconds=remaining()
                )
                if not columns:
                    raise DashboardBuildError("query returned no columns")
                create_from_spec(
                    {
                        **derived_spec,
                        "query": query_text,
                        "data_source_id": derived_spec.get("data_source_id") or results_data_source_id,
                    },
                    columns,
                    rows,
                )
            except (RuntimeError, DashboardBuildError) as exc:
                warnings.append(f"Derived query {derived_name!r} failed and was skipped: {exc}")

    # Phase 3: create the dashboard and place widgets.
    dashboard = request("POST", "/api/dashboards", body={"name": name})
    if not isinstance(dashboard, dict) or not dashboard.get("id"):
        raise DashboardBuildError(f"Failed to create dashboard {name!r}: {dashboard}")
    dashboard_id = dashboard["id"]

    viz_id_to_type = {
        viz["id"]: viz["type"]
        for entry in created_queries
        for viz in entry["visualizations"]
        if viz.get("id")
    }

    layout_items: list[dict[str, Any]] = []
    widget_specs: list[dict[str, Any]] = []
    for widget_spec in widgets:
        text = widget_spec.get("text")
        viz_ref = widget_spec.get("visualization") or widget_spec.get("visualization_name")
        viz_id: Optional[int] = widget_spec.get("visualization_id")
        if viz_ref and viz_id is None:
            viz_id = viz_name_to_id.get(str(viz_ref))
            if viz_id is None:
                warnings.append(f"Widget references unknown visualization {viz_ref!r}; skipped.")
                continue
        if viz_id is None and text is None:
            warnings.append(f"Widget spec has neither visualization nor text; skipped: {widget_spec}")
            continue
        layout_items.append(
            {
                "visualization_type": viz_id_to_type.get(viz_id) if viz_id else None,
                "text": text,
                "role": widget_spec.get("role"),
                "position": widget_spec.get("position"),
            }
        )
        widget_specs.append({"visualization_id": viz_id, "text": text, "ref": viz_ref})

    positions = plan_dashboard_layout(layout_items)

    created_widgets: list[dict[str, Any]] = []
    for widget_spec, position in zip(widget_specs, positions):
        widget = request(
            "POST",
            "/api/widgets",
            body={
                "dashboard_id": dashboard_id,
                "visualization_id": widget_spec["visualization_id"],
                "text": widget_spec["text"],
                "options": normalize_widget_options(position=position),
                "width": 1,
            },
        )
        created_widgets.append(
            {
                "id": widget.get("id") if isinstance(widget, dict) else None,
                "visualization": widget_spec["ref"],
                "text_preview": (widget_spec["text"] or "")[:60] or None,
                "position": position,
            }
        )

    # Phase 4: publish and summarize.
    if publish:
        request(
            "POST",
            f"/api/dashboards/{dashboard_id}",
            body={"is_draft": False, "version": dashboard.get("version")},
        )
    final = request("GET", f"/api/dashboards/{dashboard_id}")
    final = final if isinstance(final, dict) else {}
    slug = final.get("slug") or dashboard.get("slug") or ""

    return {
        "dashboard_id": dashboard_id,
        "name": name,
        "slug": slug,
        "url_path": f"/dashboards/{dashboard_id}-{slug}" if slug else f"/dashboards/{dashboard_id}",
        "is_draft": final.get("is_draft", not publish),
        "queries": created_queries,
        "widgets": created_widgets,
        "layout_summary": summarize_dashboard_layout(
            final.get("widgets") if isinstance(final.get("widgets"), list) else []
        ),
        "warnings": warnings,
    }
