"""Visualization option builders for the assistant."""

from __future__ import annotations

import re
from typing import Any, Optional

_DATE_NAME_HINTS = ("date", "time", "timestamp", "day", "month", "year", "created", "updated", "period")
_LAT_NAME_HINTS = ("lat", "latitude")
_LON_NAME_HINTS = ("lon", "lng", "long", "longitude")
_ISO_DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}")
_PLACEHOLDER_COLUMN_RE = re.compile(
    r"^(<[^>]+>|x_column|y_column|column_with_value|metric_column|region_code_column|lat|lon|lng)$",
    re.IGNORECASE,
)
_ID_COLUMN_RE = re.compile(r"^(id|.*_id)$", re.IGNORECASE)


def _normalize_column_key(name: str) -> str:
    return re.sub(r"[^a-z0-9]+", "", name.lower())


def _sample_values(column: str, rows: list[dict[str, Any]], limit: int = 5) -> list[Any]:
    values = []
    for row in rows[:limit]:
        if isinstance(row, dict) and column in row and row[column] is not None:
            values.append(row[column])
    return values


def is_placeholder_column(name: str) -> bool:
    if not name or not isinstance(name, str):
        return True
    stripped = name.strip()
    if not stripped:
        return True
    if stripped.startswith("<") and stripped.endswith(">"):
        return True
    return bool(_PLACEHOLDER_COLUMN_RE.match(stripped))


def _tokenize_column_name(name: str) -> list[str]:
    return [token for token in re.split(r"[_\s.]+", name.lower()) if len(token) > 1]


def _pick_best_partial_match(requested: str, matches: list[str]) -> Optional[str]:
    if not matches:
        return None
    if len(matches) == 1:
        return matches[0]

    requested_lower = requested.lower()
    if "price" in requested_lower:
        close_match = next((column for column in matches if "close" in column.lower()), None)
        if close_match:
            return close_match
    if "volume" in requested_lower:
        log_match = next((column for column in matches if "volume" in column.lower()), None)
        if log_match:
            return log_match
    return matches[0]


def resolve_column_name(
    requested: str,
    available_columns: list[str],
    rows: Optional[list[dict[str, Any]]] = None,
    *,
    role_hint: Optional[str] = None,
) -> Optional[str]:
    """Map a requested column name to an actual result column."""
    rows = rows or []
    if not available_columns:
        return None
    if is_placeholder_column(requested):
        requested = ""

    if requested:
        if requested in available_columns:
            return requested
        lower = requested.lower()
        for column in available_columns:
            if column.lower() == lower:
                return column
        normalized = _normalize_column_key(requested)
        for column in available_columns:
            if _normalize_column_key(column) == normalized:
                return column
        for column in available_columns:
            col_norm = _normalize_column_key(column)
            if normalized and (normalized in col_norm or col_norm in normalized):
                return column
        if not re.search(r"_lag_\d+$", requested, re.IGNORECASE):
            for lag in (1, 7, 14, 30):
                lagged = f"{requested}_lag_{lag}"
                if lagged in available_columns:
                    return lagged
                lagged_lower = lagged.lower()
                for column in available_columns:
                    if column.lower() == lagged_lower:
                        return column
        req_tokens = _tokenize_column_name(requested)
        if req_tokens:
            partial_matches = [
                column
                for column in available_columns
                if all(token in column.lower() for token in req_tokens)
            ]
            best = _pick_best_partial_match(requested, partial_matches)
            if best:
                return best

    if role_hint == "x":
        return next((col for col in available_columns if _looks_like_date_column(col, rows)), available_columns[0])
    if role_hint == "y":
        numeric = [col for col in available_columns if _looks_numeric_column(col, rows) and not _looks_like_id_column(col, rows)]
        if numeric:
            return numeric[0]
    if role_hint == "lat":
        return next((col for col in available_columns if _looks_like_lat_column(col)), None)
    if role_hint == "lon":
        return next((col for col in available_columns if _looks_like_lon_column(col)), None)
    return None


def _looks_like_id_column(column: str, rows: list[dict[str, Any]]) -> bool:
    if _ID_COLUMN_RE.match(column):
        return True
    values = _sample_values(column, rows, limit=20)
    # The all-ints-and-unique heuristic needs enough samples to be meaningful;
    # with only a handful of rows (e.g. single-row KPI queries) any metric
    # column would be misclassified as an id.
    if len(values) < 5:
        return False
    if all(isinstance(value, int) for value in values):
        return len(set(values)) == len(values)
    return False


def _looks_like_date_column(column: str, rows: list[dict[str, Any]]) -> bool:
    name = column.lower()
    if any(hint in name for hint in _DATE_NAME_HINTS):
        return True
    for value in _sample_values(column, rows):
        if isinstance(value, (int, float)) and 1_000_000_000 <= float(value) <= 4_000_000_000:
            return True
        text = str(value)
        if _ISO_DATE_RE.match(text):
            return True
    return False


def _looks_numeric_column(column: str, rows: list[dict[str, Any]]) -> bool:
    for value in _sample_values(column, rows):
        if isinstance(value, bool):
            return False
        if isinstance(value, (int, float)):
            return True
        try:
            float(str(value).replace(",", ""))
            return True
        except (TypeError, ValueError):
            continue
    name = column.lower()
    numeric_hints = (
        "tvl",
        "value",
        "amount",
        "count",
        "total",
        "price",
        "volume",
        "usd",
        "score",
        "cap",
        "apy",
        "rate",
        "balance",
        "supply",
    )
    return any(hint in name for hint in numeric_hints)


def _looks_like_lat_column(column: str) -> bool:
    name = column.lower()
    return any(hint in name for hint in _LAT_NAME_HINTS)


def _looks_like_lon_column(column: str) -> bool:
    name = column.lower()
    return any(hint in name for hint in _LON_NAME_HINTS)


def _pick_x_column(columns: list[str], rows: list[dict[str, Any]]) -> str:
    date_col = next((col for col in columns if _looks_like_date_column(col, rows)), None)
    if date_col:
        return date_col
    non_numeric = [col for col in columns if not _looks_numeric_column(col, rows)]
    if non_numeric:
        return non_numeric[0]
    return columns[0]


def _pick_y_columns(columns: list[str], rows: list[dict[str, Any]], x_col: str) -> list[str]:
    numeric = [
        col
        for col in columns
        if col != x_col and _looks_numeric_column(col, rows) and not _looks_like_id_column(col, rows)
    ]
    if numeric:
        return numeric
    fallback = next((col for col in columns if col != x_col), x_col)
    return [fallback]


def suggest_chart_options(
    columns: list[str],
    rows: Optional[list[dict[str, Any]]] = None,
    *,
    series_type: Optional[str] = None,
) -> dict[str, Any]:
    """Build CHART options.columnMapping from validated query columns."""
    rows = rows or []
    if not columns:
        return {
            "globalSeriesType": series_type or "column",
            "columnMapping": {},
            "legend": {"enabled": True},
            "sortX": True,
        }

    if series_type is None:
        series_type = "line" if any(_looks_like_date_column(c, rows) for c in columns) else "column"

    x_col = _pick_x_column(columns, rows)
    y_cols = _pick_y_columns(columns, rows, x_col)
    column_mapping: dict[str, str] = {x_col: "x"}
    for y_col in y_cols:
        column_mapping[y_col] = "y"

    return {
        "globalSeriesType": series_type,
        "columnMapping": column_mapping,
        "legend": {"enabled": True},
        "sortX": True,
    }


def suggest_counter_options(columns: list[str], rows: Optional[list[dict[str, Any]]] = None) -> dict[str, Any]:
    rows = rows or []
    numeric = [
        col for col in columns if _looks_numeric_column(col, rows) and not _looks_like_id_column(col, rows)
    ]
    col = numeric[0] if numeric else (columns[0] if columns else "")
    return {
        "counterColName": col,
        "counterLabel": "",
        "rowNumber": 1,
        "targetRowNumber": 1,
    }


def suggest_map_options(columns: list[str], rows: Optional[list[dict[str, Any]]] = None) -> dict[str, Any]:
    rows = rows or []
    lat = resolve_column_name("", columns, rows, role_hint="lat") or ""
    lon = resolve_column_name("", columns, rows, role_hint="lon") or ""
    return {
        "latColName": lat,
        "lonColName": lon,
        "clusterMarkers": True,
    }


def suggest_choropleth_options(columns: list[str], rows: Optional[list[dict[str, Any]]] = None) -> dict[str, Any]:
    rows = rows or []
    x_col = _pick_x_column(columns, rows)
    y_cols = _pick_y_columns(columns, rows, x_col)
    return {
        "mapType": "countries",
        "keyColumn": x_col,
        "valueColumn": y_cols[0] if y_cols else x_col,
    }


def suggest_visualization_options(
    viz_type: str,
    columns: list[str],
    rows: Optional[list[dict[str, Any]]] = None,
) -> dict[str, Any]:
    viz_type = (viz_type or "").upper()
    if viz_type == "CHART":
        return suggest_chart_options(columns, rows)
    if viz_type == "COUNTER":
        return suggest_counter_options(columns, rows)
    if viz_type == "MAP":
        return suggest_map_options(columns, rows)
    if viz_type == "CHOROPLETH":
        return suggest_choropleth_options(columns, rows)
    return {}


def _normalize_chart_options(
    options: dict[str, Any],
    columns: list[str],
    rows: list[dict[str, Any]],
) -> tuple[dict[str, Any], list[str]]:
    suggested = suggest_chart_options(columns, rows, series_type=options.get("globalSeriesType"))
    normalized = dict(suggested)
    normalized.update({k: v for k, v in options.items() if k != "columnMapping"})
    corrections: list[str] = []

    raw_mapping = options.get("columnMapping")
    if not isinstance(raw_mapping, dict) or not raw_mapping:
        normalized["columnMapping"] = suggested["columnMapping"]
        return normalized, corrections

    resolved_mapping: dict[str, str] = {}
    for requested_col, role in raw_mapping.items():
        if role not in {"x", "y", "series", "seriesA", "seriesB", "unused"}:
            corrections.append(f"Ignored unknown column role {role!r} for {requested_col!r}.")
            continue
        resolved = resolve_column_name(requested_col, columns, rows, role_hint=role if role in {"x", "y"} else None)
        if resolved:
            if resolved != requested_col:
                corrections.append(f"Mapped column {requested_col!r} → {resolved!r} ({role}).")
            resolved_mapping[resolved] = role
        else:
            corrections.append(f"Column {requested_col!r} not in query results; dropped from columnMapping.")

    if "x" not in resolved_mapping.values():
        x_col = _pick_x_column(columns, rows)
        resolved_mapping[x_col] = "x"
        corrections.append(f"Added missing x-axis column {x_col!r}.")
    if "y" not in resolved_mapping.values():
        x_col = next(name for name, role in resolved_mapping.items() if role == "x")
        for y_col in _pick_y_columns(columns, rows, x_col):
            resolved_mapping[y_col] = "y"
        corrections.append("Added missing y-axis column(s) from query results.")

    normalized["columnMapping"] = resolved_mapping
    if not options.get("globalSeriesType"):
        normalized["globalSeriesType"] = suggested["globalSeriesType"]
    return normalized, corrections


def _normalize_counter_options(
    options: dict[str, Any],
    columns: list[str],
    rows: list[dict[str, Any]],
) -> tuple[dict[str, Any], list[str]]:
    suggested = suggest_counter_options(columns, rows)
    normalized = dict(suggested)
    normalized.update(options)
    corrections: list[str] = []
    requested = options.get("counterColName")
    if requested:
        resolved = resolve_column_name(str(requested), columns, rows, role_hint="y")
        if resolved:
            if resolved != requested:
                corrections.append(f"Mapped counterColName {requested!r} → {resolved!r}.")
            normalized["counterColName"] = resolved
        else:
            normalized["counterColName"] = suggested["counterColName"]
            corrections.append(
                f"counterColName {requested!r} not in query results; using {normalized['counterColName']!r}."
            )
    return normalized, corrections


def _normalize_map_options(
    options: dict[str, Any],
    columns: list[str],
    rows: list[dict[str, Any]],
) -> tuple[dict[str, Any], list[str]]:
    suggested = suggest_map_options(columns, rows)
    normalized = dict(suggested)
    normalized.update(options)
    corrections: list[str] = []
    for key, role in (("latColName", "lat"), ("lonColName", "lon")):
        requested = options.get(key)
        if not requested:
            continue
        resolved = resolve_column_name(str(requested), columns, rows, role_hint=role)
        if resolved:
            if resolved != requested:
                corrections.append(f"Mapped {key} {requested!r} → {resolved!r}.")
            normalized[key] = resolved
        else:
            normalized[key] = suggested[key]
            corrections.append(f"{key} {requested!r} not in query results; using {normalized[key]!r}.")
    return normalized, corrections


def _normalize_choropleth_options(
    options: dict[str, Any],
    columns: list[str],
    rows: list[dict[str, Any]],
) -> tuple[dict[str, Any], list[str]]:
    suggested = suggest_choropleth_options(columns, rows)
    normalized = dict(suggested)
    normalized.update(options)
    corrections: list[str] = []
    for key, role in (("keyColumn", "x"), ("valueColumn", "y")):
        requested = options.get(key)
        if not requested:
            continue
        resolved = resolve_column_name(str(requested), columns, rows, role_hint=role)
        if resolved:
            if resolved != requested:
                corrections.append(f"Mapped {key} {requested!r} → {resolved!r}.")
            normalized[key] = resolved
        else:
            normalized[key] = suggested[key]
            corrections.append(f"{key} {requested!r} not in query results; using {normalized[key]!r}.")
    return normalized, corrections


def normalize_visualization_options(
    viz_type: str,
    options: Optional[dict[str, Any]],
    columns: list[str],
    rows: Optional[list[dict[str, Any]]] = None,
) -> tuple[dict[str, Any], list[str]]:
    """Validate and fix visualization options against actual query columns."""
    rows = rows or []
    viz_type = (viz_type or "").upper()
    options = dict(options or {})

    if viz_type == "CHART":
        return _normalize_chart_options(options, columns, rows)
    if viz_type == "COUNTER":
        return _normalize_counter_options(options, columns, rows)
    if viz_type == "MAP":
        return _normalize_map_options(options, columns, rows)
    if viz_type == "CHOROPLETH":
        return _normalize_choropleth_options(options, columns, rows)
    return options, []


def _mapped_column_names(viz_type: str, options: Optional[dict[str, Any]]) -> list[str]:
    options = options or {}
    viz_type = (viz_type or "").upper()
    if viz_type == "CHART":
        mapping = options.get("columnMapping")
        return list(mapping.keys()) if isinstance(mapping, dict) else []
    if viz_type == "COUNTER":
        value = options.get("counterColName")
        return [str(value)] if value else []
    if viz_type == "MAP":
        return [name for name in (options.get("latColName"), options.get("lonColName")) if name]
    if viz_type == "CHOROPLETH":
        return [name for name in (options.get("keyColumn"), options.get("valueColumn")) if name]
    return []


def diagnose_visualization_options(
    viz_type: str,
    options: Optional[dict[str, Any]],
    columns: list[str],
    rows: Optional[list[dict[str, Any]]] = None,
) -> dict[str, Any]:
    """Report whether a visualization's options match live query columns."""
    rows = rows or []
    options = dict(options or {})
    viz_type = (viz_type or "").upper()
    mapped_columns = _mapped_column_names(viz_type, options)
    available = set(columns)
    invalid_columns = [
        column
        for column in mapped_columns
        if column and not is_placeholder_column(column) and column not in available
    ]
    _, corrections = normalize_visualization_options(viz_type, options, columns, rows)
    suggested_options, _ = normalize_visualization_options(
        viz_type,
        suggest_visualization_options(viz_type, columns, rows),
        columns,
        rows,
    )
    return {
        "is_healthy": not invalid_columns,
        "invalid_columns": invalid_columns,
        "mapped_columns": mapped_columns,
        "suggested_options": suggested_options,
        "corrections_preview": corrections,
    }


def enrich_visualizations_for_assistant(
    visualizations: list[dict[str, Any]],
    columns: list[str],
    rows: Optional[list[dict[str, Any]]] = None,
) -> list[dict[str, Any]]:
    """Attach per-visualization health diagnostics for get_query responses."""
    enriched: list[dict[str, Any]] = []
    for visualization in visualizations:
        if not isinstance(visualization, dict):
            continue
        item = dict(visualization)
        diagnostics = diagnose_visualization_options(
            item.get("type") or "",
            item.get("options"),
            columns,
            rows,
        )
        item["options_health"] = {
            "is_healthy": diagnostics["is_healthy"],
            "invalid_columns": diagnostics["invalid_columns"],
            "corrections_preview": diagnostics["corrections_preview"],
        }
        if not diagnostics["is_healthy"]:
            item["options_health"]["suggested_options"] = diagnostics["suggested_options"]
        enriched.append(item)
    return enriched


def build_visualization_hints(columns: list[str], rows: Optional[list[dict[str, Any]]] = None) -> dict[str, Any]:
    """Structured hints the assistant can read after run_query / validation."""
    rows = rows or []
    if not columns:
        return {"note": "No columns returned — fix the query before creating visualizations."}

    chart = suggest_chart_options(columns, rows)
    counter = suggest_counter_options(columns, rows)
    hints: dict[str, Any] = {
        "columns": columns,
        "sample_row": rows[0] if rows else None,
        "recommended": {
            "CHART": {
                "omit_options": True,
                "reason": "create_visualization auto-maps columns; pass only globalSeriesType if needed.",
                "suggested_options": chart,
            },
            "COUNTER": {
                "omit_options": True,
                "suggested_options": counter,
            },
        },
        "rules": [
            "columnMapping keys must be exact result column names (case-sensitive), e.g. market_cap.usd not market_cap.",
            "Do not use placeholder names like date, tvl, x_column unless they appear in columns.",
            "Prefer omitting options for CHART/COUNTER — the server resolves columns from query results.",
        ],
    }
    if any(_looks_like_lat_column(c) for c in columns) and any(_looks_like_lon_column(c) for c in columns):
        hints["recommended"]["MAP"] = {"suggested_options": suggest_map_options(columns, rows)}
    return hints
