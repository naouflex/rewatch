"""Help documentation catalog for the assistant."""

from __future__ import annotations

from typing import Any

# Mirrors client/app/components/HelpTrigger.jsx TYPES — relative paths under /help.
HELP_TOPICS: dict[str, dict[str, str]] = {
    "getting_started": {
        "path": "/user-guide/getting-started",
        "title": "Getting Started",
        "summary": "Overview of Rewatch: connecting data sources, writing queries, building dashboards.",
    },
    "queries": {
        "path": "/user-guide/querying",
        "title": "Queries",
        "summary": "Writing SQL queries, parameters, schedules, and sharing query results.",
    },
    "dashboards": {
        "path": "/user-guide/dashboards",
        "title": "Dashboards",
        "summary": "Building dashboards, adding widgets, filters, and sharing.",
    },
    "alerts": {
        "path": "/user-guide/alerts",
        "title": "Alerts",
        "summary": "Setting up alerts on query results and notification destinations.",
    },
    "alert_setup": {
        "path": "/user-guide/alerts/setting-up-an-alert",
        "title": "Setting Up an Alert",
        "summary": "Step-by-step guide to create an alert with thresholds and notifications.",
    },
    "query_parameters": {
        "path": "/user-guide/querying/query-parameters",
        "title": "Query Parameters",
        "summary": "Using dynamic parameters in queries (dropdowns, dates, text).",
    },
    "visualizations": {
        "path": "/user-guide/visualizations/formatting-numbers",
        "title": "Formatting Numbers",
        "summary": "Number formatting specs for charts and tables.",
    },
    "permissions": {
        "path": "/user-guide/querying/writing-queries#Managing-Query-Permissions",
        "title": "Managing Query Permissions",
        "summary": "Who can view, edit, and execute queries.",
    },
    "data_sources": {
        "path": "/data-sources",
        "title": "Data Sources",
        "summary": "Connecting databases and APIs as data sources.",
    },
    "ml_models": {
        "path": "/user-guide/ml-models",
        "title": "ML Models",
        "summary": "Training scikit-learn models on query results (Rewatch extension).",
    },
}


def search_docs(query: str, help_base_url: str) -> list[dict[str, Any]]:
    needle = query.lower()
    results = []
    for key, topic in HELP_TOPICS.items():
        haystack = f"{key} {topic['title']} {topic['summary']} {topic['path']}".lower()
        if needle in haystack:
            results.append(
                {
                    "id": key,
                    "title": topic["title"],
                    "summary": topic["summary"],
                    "url": f"{help_base_url.rstrip('/')}/help{topic['path']}",
                }
            )
    return results


def get_docs_topic(topic_id: str, help_base_url: str) -> dict[str, Any]:
    topic = HELP_TOPICS.get(topic_id)
    if not topic:
        available = ", ".join(sorted(HELP_TOPICS))
        raise ValueError(f"Unknown topic {topic_id!r}. Available: {available}")
    return {
        "id": topic_id,
        "title": topic["title"],
        "summary": topic["summary"],
        "url": f"{help_base_url.rstrip('/')}/help{topic['path']}",
    }
