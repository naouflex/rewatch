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


def preview_image_url(base_url: str, resource: str, resource_id: int | str) -> str:
    from redash.assistant.previews import preview_path

    return preview_path(base_url, resource, resource_id)


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
        data["preview_image_url"] = preview_image_url(base_url, "queries", resource_id)
        for vis in data.get("visualizations") or []:
            if isinstance(vis, dict) and vis.get("id"):
                vis["preview_image_url"] = preview_image_url(base_url, "visualizations", vis["id"])
    elif "type" in data and "query_id" in data:
        data["preview_image_url"] = preview_image_url(base_url, "visualizations", resource_id)
    elif "slug" in data and any(key in data for key in ("layout", "widgets", "dashboard_filters_enabled")):
        data["app_link"] = app_link(base_url, dashboard_path(resource_id, data["slug"]))
        data["preview_image_url"] = preview_image_url(base_url, "dashboards", resource_id)
    elif "slug" in data and "name" in data and "user_id" in data:
        data["app_link"] = app_link(base_url, dashboard_path(resource_id, data["slug"]))
        data["preview_image_url"] = preview_image_url(base_url, "dashboards", resource_id)
    elif "rearm" in data and "state" in data:
        data["app_link"] = app_link(base_url, f"/alerts/{resource_id}")

    return data


def enrich_tool_payload(payload: Any, base_url: str) -> Any:
    if isinstance(payload, dict):
        if "results" in payload and isinstance(payload["results"], list):
            payload["results"] = [
                enrich_resource_links(item, base_url) if isinstance(item, dict) else item
                for item in payload["results"]
            ]
        if "visualizations" in payload and isinstance(payload["visualizations"], list):
            payload["visualizations"] = [
                enrich_resource_links(item, base_url) if isinstance(item, dict) else item
                for item in payload["visualizations"]
            ]
        return enrich_resource_links(payload, base_url)
    if isinstance(payload, list):
        return [
            enrich_resource_links(item, base_url) if isinstance(item, dict) else item
            for item in payload
        ]
    return payload


def collect_previews(payload: Any) -> list[dict[str, str]]:
    previews: list[dict[str, str]] = []
    if isinstance(payload, dict):
        if payload.get("preview_image_url"):
            previews.append(
                {
                    "title": payload.get("name") or payload.get("title") or "Preview",
                    "preview_image_url": payload["preview_image_url"],
                }
            )
        for key in ("results", "visualizations"):
            for item in payload.get(key) or []:
                previews.extend(collect_previews(item))
    elif isinstance(payload, list):
        for item in payload:
            previews.extend(collect_previews(item))

    seen: set[str] = set()
    unique: list[dict[str, str]] = []
    for item in previews:
        if not isinstance(item, dict):
            continue
        url = item.get("preview_image_url")
        if url and url not in seen:
            seen.add(url)
            unique.append(item)
    return unique


def append_preview_markdown(reply: str, previews: list[dict[str, str]]) -> str:
    if not previews:
        return reply
    blocks = []
    seen_urls: set[str] = set()
    for preview in previews:
        if not isinstance(preview, dict):
            continue
        url = preview.get("preview_image_url")
        title = preview.get("title") or "Preview"
        if url and url not in reply and url not in seen_urls:
            seen_urls.add(url)
            blocks.append(f"![{_escape_markdown_alt(title)}]({url})")
    if not blocks:
        return reply
    return reply.rstrip() + "\n\n" + "\n".join(blocks)


def _escape_markdown_alt(text: str) -> str:
    return str(text).replace("[", "\\[").replace("]", "\\]")
