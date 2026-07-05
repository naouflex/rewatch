"""Data source hints for the assistant."""

from __future__ import annotations

from typing import Any, Optional

# Curated public JSON endpoints that work well with MAP visualizations (lat/lon columns).
EXAMPLE_JSON_MAP_QUERIES = [
    {
        "title": "Sample users with geo coordinates (jsonplaceholder)",
        "data_source_type": "json",
        "query": (
            "url: https://jsonplaceholder.typicode.com/users\n"
            "fields:\n"
            "  - name\n"
            "  - username\n"
            "  - geo.lat\n"
            "  - geo.lng\n"
            "  - address.city"
        ),
        "map_options": {"latColName": "geo.lat", "lonColName": "geo.lng", "classify": "address.city"},
    },
    {
        "title": "Recent earthquakes (USGS GeoJSON — use properties, not raw geometry)",
        "data_source_type": "json",
        "query": (
            "url: https://earthquake.usgs.gov/earthquakes/feed/v1.0/summary/2.5_day.geojson\n"
            "path: features\n"
            "fields:\n"
            "  - properties.title\n"
            "  - properties.mag\n"
            "  - properties.place\n"
            "  - properties.time"
        ),
        "map_options": None,
        "note": "This feed does not expose separate lat/lon columns; use for tables/charts or find a dataset with geo.lat/geo.lng.",
    },
]

TYPE_HINTS: dict[str, str] = {
    "json": (
        "Query language is YAML (not SQL). Each query must include `url:` (absolute or relative to the "
        "data source base URL). Optional: `path` (dot path to array in response), `fields` (columns to keep), "
        "`params`, `headers`. Test with run_query using query_text + data_source_id before create_query."
    ),
    "pg": "PostgreSQL — use SQL.",
    "postgres": "PostgreSQL — use SQL.",
    "mysql": "MySQL — use SQL.",
    "bigquery": "BigQuery — use SQL.",
    "clickhouse": "ClickHouse — use SQL.",
    "sqlite": "SQLite — use SQL.",
    "mongodb": "MongoDB — query language is JSON.",
    "google_spreadsheets": "Google Sheets — query language is JSON.",
}


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
    hint = TYPE_HINTS.get(ds_type)
    if hint:
        data_source["assistant_hint"] = hint
    if ds_type == "json":
        base = _base_url(data_source.get("options"))
        data_source["assistant_json_base_url"] = base or ""
        data_source["assistant_example_queries"] = EXAMPLE_JSON_MAP_QUERIES
    return data_source


def enrich_data_sources(payload: Any) -> Any:
    if isinstance(payload, list):
        enriched = [enrich_data_source(item) if isinstance(item, dict) else item for item in payload]
        types = sorted({(item.get("type") or "").lower() for item in enriched if isinstance(item, dict) and item.get("type")})
        result: dict[str, Any] = {
            "data_sources": enriched,
            "available_types": types,
            "assistant_note": (
                "Pick a data source by id and type before create_query. "
                "For JSON/URL data and map visualizations, prefer type `json`. "
                "Use web_search + fetch_url to find public JSON URLs — never invent sample JSON."
            ),
        }
        if "json" not in types:
            result["assistant_warning"] = (
                "No JSON data source is configured. Ask an admin to add a JSON data source "
                "(Settings → Data Sources) to query public JSON/GeoJSON URLs."
            )
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
