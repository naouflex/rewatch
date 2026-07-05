"""Rewatch app link helpers (path-based routing, no hash URLs)."""

from __future__ import annotations

import re
from typing import Any

# https://host/#/queries/5 or https://host/#/dashboards/1-slug
_FULL_HASH_ROUTE_RE = re.compile(r"(https?://[^/\s)\]]+)/#/", re.IGNORECASE)

# Markdown or plain relative hash routes: /#/queries/5
_RELATIVE_HASH_ROUTE_RE = re.compile(r"(?<![:/])/#/", re.IGNORECASE)


def normalize_app_path(path: str) -> str:
    """Turn '#/queries/5' or 'queries/5' into '/queries/5'."""
    path = (path or "").strip()
    if path.startswith("#/"):
        path = path[1:]
    if path and not path.startswith("/"):
        path = f"/{path}"
    return path


def app_link(base_url: str, path: str) -> str:
    """Build an absolute in-app URL without hash routing."""
    return f"{base_url.rstrip('/')}{normalize_app_path(path)}"


def dashboard_path(dashboard_id: int | str, slug: str) -> str:
    return f"/dashboards/{dashboard_id}-{slug}"


def normalize_reply_links(text: str) -> str:
    """Rewrite legacy hash-style SPA links to path-based URLs."""
    if not text:
        return text
    text = _FULL_HASH_ROUTE_RE.sub(r"\1/", text)
    text = _RELATIVE_HASH_ROUTE_RE.sub("/", text)
    return text


def enrich_resource_links(data: dict, base_url: str) -> dict:
    """Add app_link fields so the model copies correct URLs from tool output."""
    if not isinstance(data, dict) or "id" not in data:
        return data

    resource_id = data["id"]
    if "query_hash" in data or (isinstance(data.get("query"), str) and "data_source_id" in data):
        data["app_link"] = app_link(base_url, f"/queries/{resource_id}")
    elif "slug" in data and any(key in data for key in ("layout", "widgets", "dashboard_filters_enabled")):
        data["app_link"] = app_link(base_url, dashboard_path(resource_id, data["slug"]))
    elif "slug" in data and "name" in data and "user_id" in data:
        data["app_link"] = app_link(base_url, dashboard_path(resource_id, data["slug"]))
    elif "rearm" in data and "state" in data:
        data["app_link"] = app_link(base_url, f"/alerts/{resource_id}")

    return data


def enrich_tool_payload(payload: Any, base_url: str) -> Any:
    if isinstance(payload, dict):
        if "results" in payload and isinstance(payload["results"], list):
            payload["results"] = [enrich_resource_links(item, base_url) for item in payload["results"]]
        return enrich_resource_links(payload, base_url)
    if isinstance(payload, list):
        return [enrich_resource_links(item, base_url) if isinstance(item, dict) else item for item in payload]
    return payload
