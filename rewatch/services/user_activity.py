"""Aggregate user activity from the events audit log."""

from __future__ import annotations

from collections import defaultdict
from datetime import date, datetime, timedelta, timezone
from typing import Any

from sqlalchemy import func

from rewatch.models import Event, db

# Passive actions that should not count as contributions.
EXCLUDED_ACTIONS = frozenset(
    {
        "list",
        "search",
        "api_get",
        "load_favorites",
    }
)

# Page/screen views are too noisy for a contribution chart.
PASSIVE_VIEW_OBJECT_TYPES = frozenset({"page", "screen"})

# Normalize server/client execute variants for breakdown charts.
ACTION_LABELS = {
    "execute": "Executions",
    "execute_query": "Executions",
    "cancel_execute": "Executions",
    "view": "Views",
    "create": "Created",
    "edit": "Edits",
    "fork": "Forks",
    "archive": "Archives",
    "edit_name": "Renames",
    "edit_tags": "Tag edits",
    "edit_schedule": "Schedule edits",
    "toggle_published": "Publish toggles",
    "favorite": "Favorites",
    "unfavorite": "Unfavorites",
    "copy": "Copies",
    "train": "Model training",
    "predict": "Predictions",
    "delete": "Deletes",
}

OBJECT_TYPE_LABELS = {
    "query": "Queries",
    "dashboard": "Dashboards",
    "alert": "Alerts",
    "visualization": "Visualizations",
    "widget": "Widgets",
    "data_source": "Data sources",
    "indexer": "Indexers",
    "ml_model": "ML models",
    "destination": "Destinations",
    "query_snippet": "Query snippets",
    "forum_post": "Community posts",
    "page": "Pages",
}


def _is_contribution(action: str | None, object_type: str | None) -> bool:
    action = action or ""
    object_type = object_type or ""

    if action in EXCLUDED_ACTIONS:
        return False
    if action == "view" and object_type in PASSIVE_VIEW_OBJECT_TYPES:
        return False
    return bool(action)


def _normalize_action(action: str) -> str:
    if action in ("execute", "execute_query", "cancel_execute"):
        return "execute"
    return action


def _day_key(value) -> str:
    # datetime is a date subclass; check it first so we normalize to YYYY-MM-DD.
    if isinstance(value, datetime):
        return value.date().isoformat()
    if isinstance(value, date):
        return value.isoformat()
    return str(value)[:10]


def _compute_streak(day_counts: dict[str, int], end_day: date) -> int:
    streak = 0
    current = end_day
    while day_counts.get(current.isoformat(), 0) > 0:
        streak += 1
        current -= timedelta(days=1)
    return streak


def get_user_activity_summary(user, org, days: int = 365) -> dict[str, Any]:
    days = max(7, min(days, 366))
    end_day = datetime.now(timezone.utc).date()
    start_day = end_day - timedelta(days=days - 1)
    since = datetime.combine(start_day, datetime.min.time(), tzinfo=timezone.utc)

    rows = (
        db.session.query(
            func.date_trunc("day", Event.created_at).label("day"),
            Event.action,
            Event.object_type,
            func.count().label("count"),
        )
        .filter(
            Event.org_id == org.id,
            Event.user_id == user.id,
            Event.created_at >= since,
        )
        .group_by("day", Event.action, Event.object_type)
        .all()
    )

    daily: dict[str, dict[str, Any]] = {}
    by_action: dict[str, int] = defaultdict(int)
    by_object_type: dict[str, int] = defaultdict(int)
    total = 0

    for row in rows:
        if not _is_contribution(row.action, row.object_type):
            continue

        day = _day_key(row.day)
        count = int(row.count)
        total += count

        if day not in daily:
            daily[day] = {"date": day, "count": 0, "actions": defaultdict(int)}
        daily[day]["count"] += count

        normalized = _normalize_action(row.action or "")
        daily[day]["actions"][normalized] += count
        by_action[normalized] += count

        object_type = row.object_type or "other"
        by_object_type[object_type] += count

    # Fill missing days with zero counts for heatmap continuity.
    daily_series = []
    current = start_day
    day_counts: dict[str, int] = {}
    while current <= end_day:
        key = current.isoformat()
        if key in daily:
            entry = daily[key]
            actions = dict(entry["actions"])
            daily_series.append({"date": key, "count": entry["count"], "actions": actions})
            day_counts[key] = entry["count"]
        else:
            daily_series.append({"date": key, "count": 0, "actions": {}})
            day_counts[key] = 0
        current += timedelta(days=1)

    week_start = end_day - timedelta(days=6)
    prev_week_start = end_day - timedelta(days=13)
    prev_week_end = end_day - timedelta(days=7)

    week_total = sum(
        day_counts.get((week_start + timedelta(days=i)).isoformat(), 0) for i in range(7)
    )
    prev_week_total = sum(
        day_counts.get((prev_week_start + timedelta(days=i)).isoformat(), 0) for i in range(7)
    )

    week_series = [
        {
            "date": (week_start + timedelta(days=i)).isoformat(),
            "count": day_counts.get((week_start + timedelta(days=i)).isoformat(), 0),
        }
        for i in range(7)
    ]

    action_breakdown = [
        {"key": key, "label": ACTION_LABELS.get(key, key.replace("_", " ").title()), "count": count}
        for key, count in sorted(by_action.items(), key=lambda item: (-item[1], item[0]))
        if count > 0
    ]

    object_breakdown = [
        {
            "key": key,
            "label": OBJECT_TYPE_LABELS.get(key, key.replace("_", " ").title()),
            "count": count,
        }
        for key, count in sorted(by_object_type.items(), key=lambda item: (-item[1], item[0]))
        if count > 0
    ]

    return {
        "days": days,
        "total": total,
        "week_total": week_total,
        "prev_week_total": prev_week_total,
        "week_change": week_total - prev_week_total,
        "streak": _compute_streak(day_counts, end_day),
        "daily": daily_series,
        "week": week_series,
        "by_action": action_breakdown,
        "by_object_type": object_breakdown,
    }
