"""Data source enrichment for the assistant."""

from __future__ import annotations

from typing import Any, Optional

from redash.assistant.catalog import get_query_runner_type, summarize_runner_for_type


def _base_url(options: Any) -> Optional[str]:
    if isinstance(options, dict):
        base = options.get("base_url") or options.get("url")
        if base:
            return str(base).rstrip("/")
    return None


def enrich_data_source(data_source: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(data_source, dict):
        return data_source

    ds_type = (data_source.get("type") or "").lower()
    runner_summary = summarize_runner_for_type(ds_type)
    if runner_summary:
        data_source["query_runner"] = runner_summary

    if ds_type == "json":
        base = _base_url(data_source.get("options"))
        data_source["json_base_url"] = base or ""
        # Full type docs including example_query when present
        type_docs = get_query_runner_type("json")
        if isinstance(type_docs, dict) and not type_docs.get("error"):
            notes = type_docs.get("type_notes") or {}
            if notes.get("example_query"):
                data_source["example_query"] = notes["example_query"]

    return data_source


def enrich_data_sources(payload: Any) -> Any:
    if isinstance(payload, list):
        enriched = [enrich_data_source(item) if isinstance(item, dict) else item for item in payload]
        types = sorted(
            {(item.get("type") or "").lower() for item in enriched if isinstance(item, dict) and item.get("type")}
        )
        result: dict[str, Any] = {
            "data_sources": enriched,
            "available_types": types,
            "assistant_note": (
                "Each data source includes query_runner (syntax + summary). "
                "For full query format details call get_query_runner_type with the data source `type`. "
                "Pick a data source by id before create_query."
            ),
        }
        return result
    return payload


def pick_data_source_id(payload: Any, preferred_type: str = "json") -> Optional[int]:
    if not isinstance(payload, dict):
        return None
    sources = payload.get("data_sources") or payload
    if not isinstance(sources, list):
        return None
    preferred_type = preferred_type.lower()
    for item in sources:
        if isinstance(item, dict) and (item.get("type") or "").lower() == preferred_type:
            return item.get("id")
    for item in sources:
        if isinstance(item, dict) and item.get("id"):
            return item.get("id")
    return None
