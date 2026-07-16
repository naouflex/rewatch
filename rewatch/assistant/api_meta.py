"""OpenAPI meta-tools for full REST API coverage in the in-app assistant."""

from __future__ import annotations

import json
from typing import Any, Callable, Optional

RequestFn = Callable[..., Any]

_spec_cache: Optional[dict[str, Any]] = None


def _get_spec(request: RequestFn) -> dict[str, Any]:
    global _spec_cache
    if _spec_cache is None:
        _spec_cache = request("GET", "/api/spec")
    return _spec_cache


def clear_spec_cache() -> None:
    global _spec_cache
    _spec_cache = None


def list_endpoints(
    request: RequestFn,
    *,
    tag: Optional[str] = None,
    search: Optional[str] = None,
) -> str:
    spec = _get_spec(request)
    lines: list[str] = []
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
        available = sorted({t["name"] for t in _get_spec(request).get("tags", [])})
        return f"No endpoints matched. Available tags: {', '.join(available)}"
    return "\n".join(sorted(lines))


def describe_endpoint(request: RequestFn, *, method: str, path: str) -> dict[str, Any]:
    spec = _get_spec(request)
    ops = spec.get("paths", {}).get(path)
    if ops is None:
        candidates = [p for p in spec.get("paths", {}) if path.strip("/") in p]
        hint = f" Did you mean one of: {', '.join(candidates[:10])}?" if candidates else ""
        raise RuntimeError(f"Unknown path {path!r}.{hint}")
    op = ops.get(method.lower())
    if op is None:
        available = ", ".join(m.upper() for m in ops)
        raise RuntimeError(f"Path {path} does not support {method.upper()}. Available: {available}")
    return op


# The assistant executes tools autonomously (no per-call approval UI), and web
# content fetched by other tools flows into the same LLM context. Keep the
# blast radius of a prompt-injected call_api small: no DELETE, and no
# mutations of admin-level resources.
_PROTECTED_PATH_PREFIXES = (
    "/api/users",
    "/api/groups",
    "/api/organization",
    "/api/settings",
    "/api/data_sources",
)


def call_api(
    request: RequestFn,
    *,
    method: str,
    path: str,
    query_params: Optional[dict] = None,
    body: Optional[dict] = None,
) -> Any:
    if "{" in path:
        raise RuntimeError(
            f"Path {path!r} still contains a template placeholder; substitute real values first."
        )
    method_upper = (method or "GET").upper()
    if method_upper == "DELETE":
        raise RuntimeError(
            "call_api does not allow DELETE. Use the dedicated tools "
            "(delete_alert, delete_widget, delete_visualization, archive_query) "
            "for the supported destructive operations."
        )
    normalized = "/" + path.lstrip("/")
    if method_upper != "GET" and any(
        normalized == prefix or normalized.startswith(prefix + "/") for prefix in _PROTECTED_PATH_PREFIXES
    ):
        raise RuntimeError(
            f"call_api does not allow {method_upper} on {normalized}: user, group, organization, "
            "settings, and data source administration must be done by the user in the Rewatch UI."
        )
    return request(method, path, params=query_params, body=body)


def format_endpoint_details(op: dict[str, Any]) -> str:
    return json.dumps(op, indent=2, default=str)
