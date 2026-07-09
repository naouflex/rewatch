#!/usr/bin/env python3
"""Create the Montpellier train stations dashboard from SNCF Navitia API.

Fetches departures and arrivals for Montpellier Saint-Roch and
Montpellier Sud de France via api.sncf.com, then builds derived boards
and summary charts.
"""

from __future__ import annotations

from dashboard_script_utils import build_and_report

DS_PYTHON = 4

SNCF_API_KEY = "f830dbc4-8108-4786-8303-509c08b102e9"
REGION = "sncf"
COUNT = 25
HISTORY_DAYS = 14
DASHBOARD_ID = 10
FEED_QUERY_ID = 117

STATIONS = [
    {"id": "stop_area:SNCF:87773002", "encoded_id": "stop_area%3ASNCF%3A87773002", "name": "Montpellier Saint-Roch", "short": "Saint-Roch"},
    {"id": "stop_area:SNCF:87688887", "encoded_id": "stop_area%3ASNCF%3A87688887", "name": "Montpellier Sud de France", "short": "Sud de France"},
]

COLORS = {
    "departures": "#12B886",
    "arrivals": "#4263EB",
    "saint_roch": "#7950F2",
    "sud_france": "#FA5252",
}

PY_COMMON = """
import requests
import datetime
import time

SNCF_BASE = "https://api.sncf.com/v1"
SNCF_API_KEY = "%(api_key)s"
REGION = "%(region)s"
COUNT = %(count)d
HISTORY_DAYS = %(history_days)d
STATIONS = %(stations)s


def navitia_get(path, params=None, requests=requests, SNCF_BASE=SNCF_BASE, SNCF_API_KEY=SNCF_API_KEY):
    params = params or {}
    resp = requests.get(
        SNCF_BASE + path,
        headers={"Authorization": SNCF_API_KEY},
        params=params,
        timeout=30,
    )
    if resp.status_code >= 400:
        raise Exception("SNCF API %%s: %%s" %% (resp.status_code, resp.text[:300]))
    return resp.json()


def fmt_navitia_time(value, datetime=datetime):
    if not value or len(value) < 13:
        return ""
    try:
        dt = datetime.datetime.strptime(value[:15], "%%Y%%m%%dT%%H%%M%%S")
        return dt.strftime("%%H:%%M")
    except Exception:
        return value[9:11] + ":" + value[11:13]


def link_names(links, lookup, category):
    return ", ".join(lookup.get(item.get("id"), "") for item in links if item.get("category") == category and lookup.get(item.get("id")))


def board_row(station, board_type, item, origins, terminus, fmt_navitia_time=fmt_navitia_time, link_names=link_names):
    display = item.get("display_informations") or {}
    stop_dt = item.get("stop_date_time") or {}
    links = stop_dt.get("links") or []

    if board_type == "departure":
        event_raw = stop_dt.get("departure_date_time") or ""
        event_label = fmt_navitia_time(event_raw)
        route = display.get("direction") or ""
        provenance = link_names(links, origins, "origin")
    else:
        event_raw = stop_dt.get("arrival_date_time") or ""
        event_label = fmt_navitia_time(event_raw)
        route = display.get("direction") or ""
        provenance = link_names(links, origins, "origin")

    freshness = stop_dt.get("data_freshness") or ""
    freshness_label = "Real-time" if freshness == "realtime" else "Scheduled"

    return {
        "record_type": "live",
        "station": station["name"],
        "station_short": station["short"],
        "board_type": board_type,
        "day": "",
        "trains_count": 0,
        "time": event_label,
        "time_raw": event_raw,
        "train": display.get("headsign") or display.get("trip_short_name") or "",
        "line": display.get("code") or display.get("label") or "",
        "mode": display.get("commercial_mode") or "",
        "physical_mode": display.get("physical_mode") or "",
        "destination": route,
        "provenance": provenance,
        "company": display.get("company") or "",
        "freshness": freshness_label,
        "total_departures": 0,
        "total_arrivals": 0,
    }


def fetch_board(station, endpoint, navitia_get=navitia_get, REGION=REGION, COUNT=COUNT, time=time, board_row=board_row):
    path = "/coverage/" + REGION + "/stop_areas/" + station["encoded_id"] + "/" + endpoint
    data = navitia_get(path, {"count": COUNT, "depth": 2})
    origins = {item["id"]: item.get("name", "") for item in data.get("origins") or []}
    terminus = {item["id"]: item.get("name", "") for item in data.get("terminus") or []}
    key = "departures" if endpoint == "departures" else "arrivals"
    board_type = "departure" if endpoint == "departures" else "arrival"
    rows = []
    for item in data.get(key) or []:
        rows.append(board_row(station, board_type, item, origins, terminus))
    time.sleep(0.3)
    return rows


def fetch_daily_count(station, endpoint, day, navitia_get=navitia_get, REGION=REGION, time=time, datetime=datetime):
    path = "/coverage/" + REGION + "/stop_areas/" + station["encoded_id"] + "/" + endpoint
    from_dt = day.strftime("%%Y%%m%%dT000000")
    board_type = "departure" if endpoint == "departures" else "arrival"
    count = 0
    try:
        data = navitia_get(path, {"from_datetime": from_dt, "duration": 86400, "count": 500, "depth": 0})
        key = "departures" if endpoint == "departures" else "arrivals"
        count = len(data.get(key) or [])
    except Exception:
        count = 0
    time.sleep(0.2)
    return {
        "record_type": "daily",
        "station": station["name"],
        "station_short": station["short"],
        "board_type": board_type,
        "day": day.strftime("%%Y-%%m-%%d"),
        "trains_count": count,
        "time": "",
        "time_raw": "",
        "train": "",
        "line": "",
        "mode": "",
        "physical_mode": "",
        "destination": "",
        "provenance": "",
        "company": "",
        "freshness": "",
        "total_departures": 0,
        "total_arrivals": 0,
    }


def fetch_daily_history(station, HISTORY_DAYS=HISTORY_DAYS, fetch_daily_count=fetch_daily_count, datetime=datetime):
    rows = []
    today = datetime.date.today()
    for offset in range(0, HISTORY_DAYS):
        day = today + datetime.timedelta(days=offset)
        dep = fetch_daily_count(station, "departures", day)
        arr = fetch_daily_count(station, "arrivals", day)
        rows.append(dep)
        rows.append(arr)
    return rows
""" % {
    "api_key": SNCF_API_KEY,
    "region": REGION,
    "count": COUNT,
    "history_days": HISTORY_DAYS,
    "stations": repr(STATIONS),
}

FEED_QUERY = PY_COMMON + """
rows = []
for station in STATIONS:
    rows.extend(fetch_board(station, "departures"))
    rows.extend(fetch_board(station, "arrivals"))
    rows.extend(fetch_daily_history(station))

result = {}
add_result_column(result, "record_type", "Record type", "string")
add_result_column(result, "station", "Station", "string")
add_result_column(result, "station_short", "Station (short)", "string")
add_result_column(result, "board_type", "Board", "string")
add_result_column(result, "day", "Day", "string")
add_result_column(result, "trains_count", "Trains", "integer")
add_result_column(result, "time", "Time", "string")
add_result_column(result, "time_raw", "Time (raw)", "string")
add_result_column(result, "train", "Train", "string")
add_result_column(result, "line", "Line", "string")
add_result_column(result, "mode", "Mode", "string")
add_result_column(result, "physical_mode", "Physical mode", "string")
add_result_column(result, "destination", "Destination", "string")
add_result_column(result, "provenance", "Provenance", "string")
add_result_column(result, "company", "Company", "string")
add_result_column(result, "freshness", "Freshness", "string")
add_result_column(result, "total_departures", "Total departures", "integer")
add_result_column(result, "total_arrivals", "Total arrivals", "integer")

for row in rows:
    add_result_row(result, row)
"""

CACHED = "{{cached_query.trains}}"
LIVE = "record_type = 'live'"
DAILY = "record_type = 'daily'"


def counter(name: str, column: str, label: str = "") -> dict:
    return {"type": "COUNTER", "name": name, "counter_column": column, "counter_label": label}


def chart(name: str, chart_type: str, mapping: dict, series: dict | None = None) -> dict:
    opts: dict = {
        "globalSeriesType": chart_type,
        "columnMapping": mapping,
        "color_scheme": "Rewatch",
        "legend": {"enabled": bool(series and len(series) > 1)},
    }
    if series:
        opts["seriesOptions"] = series
    return {"type": "CHART", "name": name, "options": opts}


def multi_line_chart(name: str, mapping: dict, series: dict, *, chart_type: str = "line") -> dict:
    return {
        "type": "CHART",
        "name": name,
        "options": {
            "globalSeriesType": chart_type,
            "columnMapping": mapping,
            "color_scheme": "Rewatch",
            "seriesOptions": series,
            "legend": {"enabled": len(series) > 1},
            "xAxis": {"type": "category", "labels": {"enabled": True}},
            "sortX": True,
        },
    }


QUERIES = [
    {
        "key": "trains",
        "name": "Montpellier Trains - SNCF Navitia Feed",
        "description": "Departures and arrivals for Montpellier Saint-Roch and Sud de France.",
        "data_source_id": DS_PYTHON,
        "query": FEED_QUERY,
        "visualizations": [],
    },
]

DERIVED = [
    {
        "key": "summary",
        "name": "Montpellier Trains - Summary",
        "description": "Train counts per station and board type.",
        "query": f"""
SELECT
  station_short,
  SUM(CASE WHEN board_type = 'departure' THEN 1 ELSE 0 END) AS departures,
  SUM(CASE WHEN board_type = 'arrival' THEN 1 ELSE 0 END) AS arrivals,
  COUNT(*) AS total_trains,
  (SELECT COUNT(*) FROM {CACHED} WHERE {LIVE} AND board_type = 'departure') AS total_departures,
  (SELECT COUNT(*) FROM {CACHED} WHERE {LIVE} AND board_type = 'arrival') AS total_arrivals,
  (SELECT COUNT(*) FROM {CACHED} WHERE {LIVE} AND station_short = 'Saint-Roch' AND board_type = 'departure') AS saint_roch_departures,
  (SELECT COUNT(*) FROM {CACHED} WHERE {LIVE} AND station_short = 'Saint-Roch' AND board_type = 'arrival') AS saint_roch_arrivals,
  (SELECT COUNT(*) FROM {CACHED} WHERE {LIVE} AND station_short = 'Sud de France' AND board_type = 'departure') AS sud_france_departures,
  (SELECT COUNT(*) FROM {CACHED} WHERE {LIVE} AND station_short = 'Sud de France' AND board_type = 'arrival') AS sud_france_arrivals
FROM {CACHED}
WHERE {LIVE}
GROUP BY station_short
ORDER BY station_short
""",
        "visualizations": [
            counter("Total Departures", "total_departures", "both stations"),
            counter("Total Arrivals", "total_arrivals", "both stations"),
            counter("Saint-Roch Departures", "saint_roch_departures", "upcoming"),
            counter("Saint-Roch Arrivals", "saint_roch_arrivals", "upcoming"),
            counter("Sud de France Departures", "sud_france_departures", "upcoming"),
            counter("Sud de France Arrivals", "sud_france_arrivals", "upcoming"),
            chart(
                "Trains by Station",
                "column",
                {"station_short": "x", "departures": "y", "arrivals": "y"},
                {
                    "departures": {"name": "Departures", "color": COLORS["departures"], "type": "column"},
                    "arrivals": {"name": "Arrivals", "color": COLORS["arrivals"], "type": "column"},
                },
            ),
        ],
    },
    {
        "key": "modes",
        "name": "Montpellier Trains - By Mode",
        "description": "Distribution of upcoming trains by commercial mode.",
        "query": f"""
SELECT mode, board_type, COUNT(*) AS trains
FROM {CACHED}
WHERE {LIVE} AND mode != ''
GROUP BY mode, board_type
ORDER BY trains DESC
""",
        "visualizations": [
            chart(
                "Trains by Mode",
                "column",
                {"mode": "x", "trains": "y", "board_type": "series"},
                {"trains": {"name": "Trains", "color": COLORS["saint_roch"], "type": "column"}},
            ),
            {"type": "TABLE", "name": "Mode Breakdown"},
        ],
    },
    {
        "key": "saint_roch_dep",
        "name": "Montpellier Trains - Saint-Roch Departures",
        "description": "Upcoming departures from Montpellier Saint-Roch.",
        "query": f"""
SELECT time, train, line, mode, destination, provenance, company, freshness,
  (SELECT COUNT(*) FROM {CACHED}
   WHERE {LIVE} AND station_short = 'Saint-Roch' AND board_type = 'departure') AS total_departures
FROM {CACHED}
WHERE {LIVE} AND station_short = 'Saint-Roch' AND board_type = 'departure'
ORDER BY time_raw
""",
        "visualizations": [
            counter("Saint-Roch Dep Board", "total_departures", "trains listed"),
            {"type": "TABLE", "name": "Saint-Roch Departures Board"},
        ],
    },
    {
        "key": "saint_roch_arr",
        "name": "Montpellier Trains - Saint-Roch Arrivals",
        "description": "Upcoming arrivals at Montpellier Saint-Roch.",
        "query": f"""
SELECT time, train, line, mode, destination, provenance, company, freshness,
  (SELECT COUNT(*) FROM {CACHED}
   WHERE {LIVE} AND station_short = 'Saint-Roch' AND board_type = 'arrival') AS total_arrivals
FROM {CACHED}
WHERE {LIVE} AND station_short = 'Saint-Roch' AND board_type = 'arrival'
ORDER BY time_raw
""",
        "visualizations": [
            counter("Saint-Roch Arr Board", "total_arrivals", "trains listed"),
            {"type": "TABLE", "name": "Saint-Roch Arrivals Board"},
        ],
    },
    {
        "key": "sud_france_dep",
        "name": "Montpellier Trains - Sud de France Departures",
        "description": "Upcoming departures from Montpellier Sud de France.",
        "query": f"""
SELECT time, train, line, mode, destination, provenance, company, freshness,
  (SELECT COUNT(*) FROM {CACHED}
   WHERE {LIVE} AND station_short = 'Sud de France' AND board_type = 'departure') AS total_departures
FROM {CACHED}
WHERE {LIVE} AND station_short = 'Sud de France' AND board_type = 'departure'
ORDER BY time_raw
""",
        "visualizations": [
            counter("Sud de France Dep Board", "total_departures", "trains listed"),
            {"type": "TABLE", "name": "Sud de France Departures Board"},
        ],
    },
    {
        "key": "sud_france_arr",
        "name": "Montpellier Trains - Sud de France Arrivals",
        "description": "Upcoming arrivals at Montpellier Sud de France.",
        "query": f"""
SELECT time, train, line, mode, destination, provenance, company, freshness,
  (SELECT COUNT(*) FROM {CACHED}
   WHERE {LIVE} AND station_short = 'Sud de France' AND board_type = 'arrival') AS total_arrivals
FROM {CACHED}
WHERE {LIVE} AND station_short = 'Sud de France' AND board_type = 'arrival'
ORDER BY time_raw
""",
        "visualizations": [
            counter("Sud de France Arr Board", "total_arrivals", "trains listed"),
            {"type": "TABLE", "name": "Sud de France Arrivals Board"},
        ],
    },
    {
        "key": "history_daily",
        "name": "Montpellier Trains - Daily Volume (14d)",
        "description": "Scheduled train counts per day from SNCF timetables (next 14 days).",
        "query": f"""
SELECT
  day,
  SUM(CASE WHEN board_type = 'departure' THEN trains_count ELSE 0 END) AS departures,
  SUM(CASE WHEN board_type = 'arrival' THEN trains_count ELSE 0 END) AS arrivals,
  SUM(trains_count) AS total_trains,
  SUM(CASE WHEN station_short = 'Saint-Roch' THEN trains_count ELSE 0 END) AS saint_roch_trains,
  SUM(CASE WHEN station_short = 'Sud de France' THEN trains_count ELSE 0 END) AS sud_france_trains,
  (SELECT ROUND(CAST(SUM(trains_count) AS REAL) / COUNT(DISTINCT day), 1)
   FROM {CACHED} WHERE {DAILY}) AS avg_daily_trains,
  (SELECT MAX(daily_total) FROM (
     SELECT day, SUM(trains_count) AS daily_total
     FROM {CACHED} WHERE {DAILY}
     GROUP BY day
   )) AS peak_day_trains,
  (SELECT COUNT(DISTINCT day) FROM {CACHED} WHERE {DAILY}) AS days_tracked
FROM {CACHED}
WHERE {DAILY}
GROUP BY day
ORDER BY day
""",
        "visualizations": [
            counter("Avg Daily Trains", "avg_daily_trains", "scheduled"),
            counter("Peak Day Trains", "peak_day_trains", "busiest day"),
            counter("Days Tracked", "days_tracked", "in chart"),
            multi_line_chart(
                "Trains per Day",
                {"day": "x", "departures": "y", "arrivals": "y", "total_trains": "y"},
                {
                    "departures": {"name": "Departures", "color": COLORS["departures"], "type": "line"},
                    "arrivals": {"name": "Arrivals", "color": COLORS["arrivals"], "type": "line"},
                    "total_trains": {"name": "Total", "color": COLORS["saint_roch"], "type": "line"},
                },
            ),
            chart(
                "Daily Total Trains",
                "column",
                {"day": "x", "total_trains": "y"},
                {"total_trains": {"name": "Total trains", "color": COLORS["saint_roch"], "type": "column"}},
            ),
            multi_line_chart(
                "Trains per Day by Station",
                {"day": "x", "saint_roch_trains": "y", "sud_france_trains": "y"},
                {
                    "saint_roch_trains": {"name": "Saint-Roch", "color": COLORS["saint_roch"], "type": "line"},
                    "sud_france_trains": {"name": "Sud de France", "color": COLORS["sud_france"], "type": "line"},
                },
            ),
            {"type": "TABLE", "name": "Daily Train Breakdown"},
        ],
    },
]


def pos(col: int, row: int, size_x: int, size_y: int) -> dict:
    return {"col": col, "row": row, "sizeX": size_x, "sizeY": size_y}


WIDGETS = [
    {
        "text": (
            "# 🚆 Montpellier Train Stations\n\n"
            "Live departure and arrival boards for **Montpellier Saint-Roch** and "
            "**Montpellier Sud de France**, powered by the "
            "[SNCF Navitia API](https://doc.navitia.io/). "
            "Refresh **SNCF Navitia Feed** to update all widgets."
        ),
        "position": pos(0, 0, 12, 3),
    },
    {"text": "## Overview", "position": pos(0, 3, 12, 2)},
    {"visualization": "Total Departures", "position": pos(0, 5, 3, 8)},
    {"visualization": "Total Arrivals", "position": pos(3, 5, 3, 8)},
    {"visualization": "Saint-Roch Departures", "position": pos(6, 5, 3, 8)},
    {"visualization": "Saint-Roch Arrivals", "position": pos(9, 5, 3, 8)},
    {"visualization": "Sud de France Departures", "position": pos(0, 13, 6, 8)},
    {"visualization": "Sud de France Arrivals", "position": pos(6, 13, 6, 8)},
    {"visualization": "Trains by Station", "position": pos(0, 21, 6, 8)},
    {"visualization": "Trains by Mode", "position": pos(6, 21, 6, 8)},
    {"text": "## Montpellier Saint-Roch", "position": pos(0, 29, 12, 2)},
    {"visualization": "Saint-Roch Departures Board", "position": pos(0, 31, 6, 10)},
    {"visualization": "Saint-Roch Arrivals Board", "position": pos(6, 31, 6, 10)},
    {"text": "## Montpellier Sud de France", "position": pos(0, 41, 12, 2)},
    {"visualization": "Sud de France Departures Board", "position": pos(0, 43, 6, 10)},
    {"visualization": "Sud de France Arrivals Board", "position": pos(6, 43, 6, 10)},
    {"visualization": "Mode Breakdown", "position": pos(0, 53, 12, 8)},
    {"text": "## Daily train volume (scheduled)", "position": pos(0, 61, 12, 2)},
    {"visualization": "Avg Daily Trains", "position": pos(0, 63, 3, 8)},
    {"visualization": "Peak Day Trains", "position": pos(3, 63, 3, 8)},
    {"visualization": "Days Tracked", "position": pos(6, 63, 3, 8)},
    {"visualization": "Daily Total Trains", "position": pos(9, 63, 3, 8)},
    {"visualization": "Trains per Day", "position": pos(0, 71, 8, 8)},
    {"visualization": "Trains per Day by Station", "position": pos(8, 71, 4, 8)},
    {"visualization": "Daily Train Breakdown", "position": pos(0, 79, 12, 8)},
    {
        "text": (
            "Data: [SNCF Navitia API](https://api.sncf.com/v1) — "
            "25 upcoming departures and 25 arrivals per station. "
            "Daily volume uses scheduled timetables for the next 14 days. "
            "Times shown in Europe/Paris local time."
        ),
        "position": pos(0, 87, 12, 3),
    },
]


if __name__ == "__main__":
    import argparse

    from dashboard_script_utils import request

    parser = argparse.ArgumentParser()
    parser.add_argument("--update", action="store_true", help="Update dashboard %s in place" % DASHBOARD_ID)
    args = parser.parse_args()

    if args.update:
        from rewatch.assistant.dashboard_builder import (
            _publish_query,
            _substitute_cached_query_refs,
            refresh_queries_and_wait,
            resolve_visualization_spec,
        )

        cached_table = f"cached_query_{FEED_QUERY_ID}"
        request(
            "POST",
            f"/api/queries/{FEED_QUERY_ID}",
            body={"query": FEED_QUERY, "data_source_id": DS_PYTHON},
        )
        refresh_queries_and_wait(request, [FEED_QUERY_ID], timeout_seconds=300)

        derived_updates = {
            118: DERIVED[0]["query"].replace(CACHED, cached_table).replace(LIVE, "record_type = 'live'"),
            119: DERIVED[1]["query"].replace(CACHED, cached_table).replace(LIVE, "record_type = 'live'"),
            120: DERIVED[2]["query"].replace(CACHED, cached_table).replace(LIVE, "record_type = 'live'"),
            121: DERIVED[3]["query"].replace(CACHED, cached_table).replace(LIVE, "record_type = 'live'"),
            122: DERIVED[4]["query"].replace(CACHED, cached_table).replace(LIVE, "record_type = 'live'"),
            123: DERIVED[5]["query"].replace(CACHED, cached_table).replace(LIVE, "record_type = 'live'"),
        }
        for query_id, sql in derived_updates.items():
            request("POST", f"/api/queries/{query_id}", body={"query": sql, "data_source_id": 1})
            refresh_queries_and_wait(request, [query_id], timeout_seconds=120)

        hist_spec = DERIVED[6]
        hist_sql = hist_spec["query"].replace(CACHED, cached_table).replace(DAILY, "record_type = 'daily'")
        hist_query = request(
            "POST",
            "/api/queries",
            body={
                "name": hist_spec["name"],
                "description": hist_spec["description"],
                "query": hist_sql,
                "data_source_id": 1,
            },
        )
        hist_id = hist_query["id"]
        _publish_query(request, hist_query)
        refresh_queries_and_wait(request, [hist_id], timeout_seconds=300)
        q = request("GET", f"/api/queries/{hist_id}")
        lqd = q.get("latest_query_data_id")
        if not lqd:
            raise RuntimeError(f"History query {hist_id} has no results after refresh")
        qr = request("GET", f"/api/query_results/{lqd}")
        data = qr.get("query_result", {}).get("data", {})
        columns = [c["name"] for c in data.get("columns", [])]
        rows = data.get("rows", [])

        viz_ids = {}
        for viz_spec in hist_spec["visualizations"]:
            viz_type, viz_name, options, _ = resolve_visualization_spec(viz_spec, columns, rows)
            viz = request(
                "POST",
                "/api/visualizations",
                body={"query_id": hist_id, "type": viz_type, "name": viz_name, "options": options},
            )
            viz_ids[viz_name] = viz["id"]

        dashboard = request("GET", f"/api/dashboards/{DASHBOARD_ID}")
        max_row = 0
        for w in dashboard.get("widgets", []):
            pos_w = (w.get("options") or {}).get("position") or {}
            max_row = max(max_row, pos_w.get("row", 0) + pos_w.get("sizeY", 0))

        new_widgets = [
            {"text": "## Daily train volume (scheduled)"},
            {"visualization": "Avg Daily Trains"},
            {"visualization": "Peak Day Trains"},
            {"visualization": "Days Tracked"},
            {"visualization": "Daily Total Trains"},
            {"visualization": "Trains per Day"},
            {"visualization": "Trains per Day by Station"},
            {"visualization": "Daily Train Breakdown"},
        ]
        for widget in new_widgets:
            body = {"dashboard_id": DASHBOARD_ID, "width": 1}
            if widget.get("text"):
                body["text"] = widget["text"]
            else:
                body["visualization_id"] = viz_ids[widget["visualization"]]
            request("POST", "/api/widgets", body=body)

        print(f"Updated feed query {FEED_QUERY_ID}, derived queries, and dashboard {DASHBOARD_ID}")
        print(f"History query: {hist_id}")
        print(f"Dashboard: https://rewatch.naoufel.io/dashboards/{DASHBOARD_ID}-montpellier-train-stations")
    else:
        build_and_report(
            name="Montpellier Train Stations",
            queries=QUERIES,
            derived=DERIVED,
            widgets=WIDGETS,
            validate_before_create=False,
        )
