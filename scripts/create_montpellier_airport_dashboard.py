#!/usr/bin/env python3
"""Create the Montpellier Airport (LFMT/MPL) dashboard from FlightAware AeroAPI.

Uses a single Python query to fetch all AeroAPI data (one validation run, minimal
API quota), then derived SQL queries on cached results for boards and charts.
"""

from __future__ import annotations

from dashboard_script_utils import build_and_report

DS_PYTHON = 4
DS_RESULTS = 1

AIRPORT_ICAO = "LFMT"
AIRPORT_IATA = "MPL"
TIMEZONE = "Europe/Paris"
AEROAPI_KEY = "qOi31AGsyoUYGh4ipUceHFFSvSFmLINB"

COLORS = {
    "arrivals": "#4263EB",
    "departures": "#12B886",
    "delay": "#FA5252",
    "history_arrivals": "#4263EB",
    "history_departures": "#12B886",
    "history_total": "#7950F2",
}

PY_COMMON = """
import requests
import datetime
import time

AEROAPI_BASE = "https://aeroapi.flightaware.com/aeroapi"
AEROAPI_KEY = "%(api_key)s"


def aeroapi_get(path, params=None, requests=requests, AEROAPI_BASE=AEROAPI_BASE, AEROAPI_KEY=AEROAPI_KEY, time=time):
    params = params or {}
    last_error = None
    for attempt in range(5):
        resp = requests.get(
            AEROAPI_BASE + path,
            headers={"x-apikey": AEROAPI_KEY},
            params=params,
            timeout=30,
        )
        if resp.status_code == 429:
            last_error = resp.text[:300]
            time.sleep(min(8, 2 ** attempt))
            continue
        if resp.status_code >= 400:
            raise Exception("AeroAPI %%s: %%s" %% (resp.status_code, resp.text[:300]))
        return resp.json()
    raise Exception("AeroAPI rate limit: %%s" %% last_error)


def fmt_time(iso, datetime=datetime):
    if not iso:
        return ""
    try:
        dt = datetime.datetime.fromisoformat(iso.replace("Z", "+00:00"))
        return dt.astimezone().strftime("%%H:%%M")
    except Exception:
        return iso[:16].replace("T", " ")


def fmt_delay(seconds):
    if seconds is None:
        return ""
    minutes = int(seconds) // 60
    if minutes == 0:
        return "On time"
    prefix = "+" if minutes > 0 else ""
    return "%%s%%d min" %% (prefix, minutes)


def airport_label(ap):
    if not ap:
        return ""
    code = ap.get("code_iata") or ap.get("code_icao") or ap.get("code") or ""
    city = ap.get("city") or ""
    if city and code:
        return "%%s (%%s)" %% (city, code)
    return code or ap.get("name") or ""


def flight_row(flight, direction, board_type, fmt_time=fmt_time, fmt_delay=fmt_delay, airport_label=airport_label):
    if direction == "arrival":
        other = flight.get("origin") or {}
        sched = flight.get("scheduled_in")
        est = flight.get("estimated_in")
        actual = flight.get("actual_in")
        delay = flight.get("arrival_delay")
        gate = flight.get("gate_destination")
        terminal = flight.get("terminal_destination")
    else:
        other = flight.get("destination") or {}
        sched = flight.get("scheduled_out")
        est = flight.get("estimated_out")
        actual = flight.get("actual_out")
        delay = flight.get("departure_delay")
        gate = flight.get("gate_origin")
        terminal = flight.get("terminal_origin")

    ident = flight.get("ident_iata") or flight.get("ident") or ""
    return {
        "board_type": board_type,
        "flight": ident,
        "airline": flight.get("operator_iata") or flight.get("operator") or "",
        "route": airport_label(other),
        "aircraft": flight.get("aircraft_type") or "",
        "status": flight.get("status") or "",
        "scheduled": fmt_time(sched),
        "estimated": fmt_time(est),
        "actual": fmt_time(actual),
        "delay": fmt_delay(delay),
        "delay_min": (int(delay) // 60) if delay is not None else 0,
        "gate": gate or "",
        "terminal": terminal or "",
        "registration": flight.get("registration") or "",
        "airport": "",
        "iata": "",
        "icao": "",
        "city": "",
        "country": "",
        "elevation_ft": 0,
        "latitude": 0.0,
        "longitude": 0.0,
        "timezone": "",
    }


def flight_date(flight, direction, datetime=datetime):
    if direction == "arrival":
        ts = (
            flight.get("actual_on") or flight.get("actual_in")
            or flight.get("scheduled_on") or flight.get("scheduled_in")
        )
    else:
        ts = (
            flight.get("actual_off") or flight.get("actual_out")
            or flight.get("scheduled_off") or flight.get("scheduled_out")
        )
    if not ts:
        return ""
    return ts[:10]
""" % {"api_key": AEROAPI_KEY}

FLIGHTS_QUERY = PY_COMMON + """
icao = "%(icao)s"
info = aeroapi_get("/airports/" + icao)
time.sleep(0.5)

arrivals = aeroapi_get("/airports/" + icao + "/flights/arrivals", {"max_pages": 1}).get("arrivals") or []
time.sleep(0.5)
departures = aeroapi_get("/airports/" + icao + "/flights/departures", {"max_pages": 1}).get("departures") or []
time.sleep(0.5)
sched_arr = aeroapi_get("/airports/" + icao + "/flights/scheduled_arrivals", {"max_pages": 1}).get("scheduled_arrivals") or []
time.sleep(0.5)
sched_dep = aeroapi_get("/airports/" + icao + "/flights/scheduled_departures", {"max_pages": 1}).get("scheduled_departures") or []

result = {}
add_result_column(result, "board_type", "Board", "string")
add_result_column(result, "flight", "Flight", "string")
add_result_column(result, "airline", "Airline", "string")
add_result_column(result, "route", "Route", "string")
add_result_column(result, "aircraft", "Aircraft", "string")
add_result_column(result, "status", "Status", "string")
add_result_column(result, "scheduled", "Scheduled", "string")
add_result_column(result, "estimated", "Estimated", "string")
add_result_column(result, "actual", "Actual", "string")
add_result_column(result, "delay", "Delay", "string")
add_result_column(result, "delay_min", "Delay (min)", "integer")
add_result_column(result, "gate", "Gate", "string")
add_result_column(result, "terminal", "Terminal", "string")
add_result_column(result, "registration", "Tail", "string")
add_result_column(result, "airport", "Airport", "string")
add_result_column(result, "iata", "IATA", "string")
add_result_column(result, "icao", "ICAO", "string")
add_result_column(result, "city", "City", "string")
add_result_column(result, "country", "Country", "string")
add_result_column(result, "elevation_ft", "Elevation (ft)", "integer")
add_result_column(result, "latitude", "Latitude", "float")
add_result_column(result, "longitude", "Longitude", "float")
add_result_column(result, "timezone", "Timezone", "string")

add_result_row(result, {
    "board_type": "airport",
    "flight": "", "airline": "", "route": "", "aircraft": "", "status": "",
    "scheduled": "", "estimated": "", "actual": "", "delay": "", "delay_min": 0,
    "gate": "", "terminal": "", "registration": "",
    "airport": info.get("name") or "Montpellier",
    "iata": info.get("code_iata") or "%(iata)s",
    "icao": info.get("code_icao") or "%(icao)s",
    "city": info.get("city") or "",
    "country": info.get("country_code") or "",
    "elevation_ft": info.get("elevation") or 0,
    "latitude": info.get("latitude") or 0,
    "longitude": info.get("longitude") or 0,
    "timezone": info.get("timezone") or "%(tz)s",
})

for f in arrivals:
    add_result_row(result, flight_row(f, "arrival", "arrival"))
for f in departures:
    add_result_row(result, flight_row(f, "departure", "departure"))
for f in sched_arr:
    add_result_row(result, flight_row(f, "arrival", "scheduled_arrival"))
for f in sched_dep:
    add_result_row(result, flight_row(f, "departure", "scheduled_departure"))
""" % {"icao": AIRPORT_ICAO, "iata": AIRPORT_IATA, "tz": TIMEZONE}

HISTORY_QUERY = PY_COMMON + """
icao = "%(icao)s"
today = datetime.datetime.utcnow().date()
start = (today - datetime.timedelta(days=9)).isoformat()
end = (today + datetime.timedelta(days=1)).isoformat()
params = {"start": start, "end": end, "max_pages": 2}

hist_arr = aeroapi_get("/airports/" + icao + "/flights/arrivals", params).get("arrivals") or []
time.sleep(0.5)
hist_dep = aeroapi_get("/airports/" + icao + "/flights/departures", params).get("departures") or []

result = {}
add_result_column(result, "board_type", "Board", "string")
add_result_column(result, "flight_date", "Date", "date")
add_result_column(result, "flight", "Flight", "string")
add_result_column(result, "airline", "Airline", "string")
add_result_column(result, "route", "Route", "string")
add_result_column(result, "aircraft", "Aircraft", "string")
add_result_column(result, "status", "Status", "string")
add_result_column(result, "delay_min", "Delay (min)", "integer")

for f in hist_arr:
    row = flight_row(f, "arrival", "history_arrival")
    row["flight_date"] = flight_date(f, "arrival")
    add_result_row(result, row)
for f in hist_dep:
    row = flight_row(f, "departure", "history_departure")
    row["flight_date"] = flight_date(f, "departure")
    add_result_row(result, row)
""" % {"icao": AIRPORT_ICAO}

CACHED = "{{cached_query.flights}}"
HISTORY = "{{cached_query.history}}"


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
            "xAxis": {"type": "datetime", "labels": {"enabled": True}},
            "sortX": True,
        },
    }


QUERIES = [
    {
        "key": "flights",
        "name": "Montpellier Airport - AeroAPI Feed",
        "description": "Single fetch of airport info and all flight boards from AeroAPI.",
        "data_source_id": DS_PYTHON,
        "query": FLIGHTS_QUERY,
        "visualizations": [],
    },
    {
        "key": "history",
        "name": "Montpellier Airport - 10-Day History Feed",
        "description": "Arrivals and departures over the last 10 days from AeroAPI.",
        "data_source_id": DS_PYTHON,
        "query": HISTORY_QUERY,
        "visualizations": [],
    },
]

DERIVED = [
    {
        "key": "airport",
        "name": "Montpellier Airport - Info",
        "description": "Static airport information for LFMT/MPL.",
        "query": f"""
SELECT airport, iata, icao, city, country, elevation_ft, latitude, longitude, timezone
FROM {CACHED}
WHERE board_type = 'airport'
LIMIT 1
""",
        "visualizations": [
            counter("Airport", "airport", AIRPORT_IATA),
            counter("IATA Code", "iata", "Montpellier"),
            counter("ICAO Code", "icao", "France"),
            counter("Elevation", "elevation_ft", "ft AMSL"),
            counter("Latitude", "latitude", "°N"),
            counter("Longitude", "longitude", "°E"),
        ],
    },
    {
        "key": "arrivals",
        "name": "Montpellier Airport - Arrivals (24h)",
        "description": "Recent arrivals at Montpellier-Méditerranée.",
        "query": f"""
SELECT
  flight, airline, route, aircraft, status,
  scheduled, estimated, actual, delay, delay_min, gate, terminal, registration,
  (SELECT COUNT(*) FROM {CACHED} WHERE board_type = 'arrival') AS total_arrivals
FROM {CACHED}
WHERE board_type = 'arrival'
ORDER BY scheduled
""",
        "visualizations": [
            counter("Arrivals Today", "total_arrivals", "last 24h"),
            chart(
                "Arrival Delays",
                "column",
                {"flight": "x", "delay_min": "y"},
                {"delay_min": {"name": "Delay (min)", "color": COLORS["delay"], "type": "column"}},
            ),
            {"type": "TABLE", "name": "Arrivals Board"},
        ],
    },
    {
        "key": "departures",
        "name": "Montpellier Airport - Departures (24h)",
        "description": "Recent departures from Montpellier-Méditerranée.",
        "query": f"""
SELECT
  flight, airline, route, aircraft, status,
  scheduled, estimated, actual, delay, delay_min, gate, terminal, registration,
  (SELECT COUNT(*) FROM {CACHED} WHERE board_type = 'departure') AS total_departures
FROM {CACHED}
WHERE board_type = 'departure'
ORDER BY scheduled
""",
        "visualizations": [
            counter("Departures Today", "total_departures", "last 24h"),
            chart(
                "Departure Delays",
                "column",
                {"flight": "x", "delay_min": "y"},
                {"delay_min": {"name": "Delay (min)", "color": COLORS["departures"], "type": "column"}},
            ),
            {"type": "TABLE", "name": "Departures Board"},
        ],
    },
    {
        "key": "sched_arr",
        "name": "Montpellier Airport - Scheduled Arrivals",
        "description": "Upcoming scheduled arrivals at LFMT.",
        "query": f"""
SELECT
  flight, airline, route, aircraft, status, scheduled, estimated, gate, terminal,
  (SELECT COUNT(*) FROM {CACHED} WHERE board_type = 'scheduled_arrival') AS total_scheduled
FROM {CACHED}
WHERE board_type = 'scheduled_arrival'
ORDER BY scheduled
""",
        "visualizations": [
            counter("Scheduled Arrivals", "total_scheduled", "upcoming"),
            {"type": "TABLE", "name": "Scheduled Arrivals Board"},
        ],
    },
    {
        "key": "sched_dep",
        "name": "Montpellier Airport - Scheduled Departures",
        "description": "Upcoming scheduled departures from LFMT.",
        "query": f"""
SELECT
  flight, airline, route, aircraft, status, scheduled, estimated, gate, terminal,
  (SELECT COUNT(*) FROM {CACHED} WHERE board_type = 'scheduled_departure') AS total_scheduled
FROM {CACHED}
WHERE board_type = 'scheduled_departure'
ORDER BY scheduled
""",
        "visualizations": [
            counter("Scheduled Departures", "total_scheduled", "upcoming"),
            {"type": "TABLE", "name": "Scheduled Departures Board"},
        ],
    },
    {
        "key": "delays",
        "name": "Montpellier Airport - Delay Summary",
        "description": "Average and per-flight delays for arrivals and departures.",
        "query": f"""
SELECT
  direction,
  flight,
  route,
  delay_min,
  (SELECT ROUND(AVG(CAST(delay_min AS REAL)), 1) FROM {CACHED} WHERE board_type = 'arrival') AS avg_arrival_delay_min,
  (SELECT ROUND(AVG(CAST(delay_min AS REAL)), 1) FROM {CACHED} WHERE board_type = 'departure') AS avg_departure_delay_min
FROM (
  SELECT 'Arrival' AS direction, flight, route, delay_min
  FROM {CACHED} WHERE board_type = 'arrival'
  UNION ALL
  SELECT 'Departure', flight, route, delay_min
  FROM {CACHED} WHERE board_type = 'departure'
)
ORDER BY direction, delay_min DESC
""",
        "visualizations": [
            counter("Avg Arrival Delay", "avg_arrival_delay_min", "minutes"),
            counter("Avg Departure Delay", "avg_departure_delay_min", "minutes"),
            chart(
                "Delays by Flight",
                "column",
                {"flight": "x", "delay_min": "y", "direction": "series"},
                {"delay_min": {"name": "Delay (min)", "color": COLORS["delay"], "type": "column"}},
            ),
        ],
    },
    {
        "key": "history_daily",
        "name": "Montpellier Airport - Flights per Day (10d)",
        "description": "Daily arrival, departure, and total flight counts over the last 10 days.",
        "query": f"""
SELECT
  flight_date AS day,
  SUM(CASE WHEN board_type = 'history_arrival' THEN 1 ELSE 0 END) AS arrivals,
  SUM(CASE WHEN board_type = 'history_departure' THEN 1 ELSE 0 END) AS departures,
  COUNT(*) AS total_flights,
  ROUND(AVG(CAST(delay_min AS REAL)), 1) AS avg_delay_min,
  (SELECT COUNT(*) FROM {HISTORY} WHERE board_type LIKE 'history_%%') AS total_10d,
  (SELECT ROUND(CAST(COUNT(*) AS REAL) / COUNT(DISTINCT flight_date), 1)
   FROM {HISTORY} WHERE board_type LIKE 'history_%%') AS avg_daily_flights,
  (SELECT MAX(daily_total) FROM (
     SELECT flight_date, COUNT(*) AS daily_total
     FROM {HISTORY} WHERE board_type LIKE 'history_%%'
     GROUP BY flight_date
   )) AS peak_day_flights
FROM {HISTORY}
WHERE board_type IN ('history_arrival', 'history_departure')
  AND flight_date != ''
GROUP BY flight_date
ORDER BY flight_date
""",
        "visualizations": [
            counter("Total Flights (10d)", "total_10d", "arrivals + departures"),
            counter("Avg Daily Flights", "avg_daily_flights", "per day"),
            counter("Peak Day Volume", "peak_day_flights", "busiest day"),
            multi_line_chart(
                "Flights per Day",
                {"day": "x", "arrivals": "y", "departures": "y", "total_flights": "y"},
                {
                    "arrivals": {"name": "Arrivals", "color": COLORS["history_arrivals"], "type": "line"},
                    "departures": {"name": "Departures", "color": COLORS["history_departures"], "type": "line"},
                    "total_flights": {"name": "Total", "color": COLORS["history_total"], "type": "line"},
                },
            ),
            chart(
                "Daily Total Flights",
                "column",
                {"day": "x", "total_flights": "y"},
                {"total_flights": {"name": "Total flights", "color": COLORS["history_total"], "type": "column"}},
            ),
            chart(
                "Daily Avg Delay",
                "line",
                {"day": "x", "avg_delay_min": "y"},
                {"avg_delay_min": {"name": "Avg delay (min)", "color": COLORS["delay"], "type": "line"}},
            ),
            {"type": "TABLE", "name": "Daily Flight Breakdown"},
        ],
    },
    {
        "key": "history_airlines",
        "name": "Montpellier Airport - Top Airlines (10d)",
        "description": "Busiest airlines at LFMT over the last 10 days.",
        "query": f"""
SELECT
  airline,
  COUNT(*) AS flights,
  SUM(CASE WHEN board_type = 'history_arrival' THEN 1 ELSE 0 END) AS arrivals,
  SUM(CASE WHEN board_type = 'history_departure' THEN 1 ELSE 0 END) AS departures,
  ROUND(AVG(CAST(delay_min AS REAL)), 1) AS avg_delay_min
FROM {HISTORY}
WHERE board_type IN ('history_arrival', 'history_departure')
  AND airline != ''
GROUP BY airline
ORDER BY flights DESC
LIMIT 15
""",
        "visualizations": [
            chart(
                "Top Airlines by Volume",
                "column",
                {"airline": "x", "flights": "y"},
                {"flights": {"name": "Flights", "color": COLORS["history_total"], "type": "column"}},
            ),
            {"type": "TABLE", "name": "Airline Breakdown (10d)"},
        ],
    },
]


def pos(col: int, row: int, size_x: int, size_y: int) -> dict:
    return {"col": col, "row": row, "sizeX": size_x, "sizeY": size_y}


WIDGETS = [
    {
        "text": (
            "# ✈️ Montpellier Airport (LFMT / MPL)\n\n"
            "Live flight board for **Montpellier-Méditerranée Airport** — arrivals, "
            "departures, scheduled flights, and delay stats powered by "
            "[FlightAware AeroAPI](https://www.flightaware.com/commercial/aeroapi/). "
            "Refresh the **AeroAPI Feed** query to pull the latest data."
        ),
        "position": pos(0, 0, 12, 3),
    },
    {"text": "## Airport", "position": pos(0, 3, 12, 2)},
    {"visualization": "Airport", "position": pos(0, 5, 3, 8)},
    {"visualization": "IATA Code", "position": pos(3, 5, 3, 8)},
    {"visualization": "ICAO Code", "position": pos(6, 5, 3, 8)},
    {"visualization": "Elevation", "position": pos(9, 5, 3, 8)},
    {"visualization": "Latitude", "position": pos(0, 13, 6, 8)},
    {"visualization": "Longitude", "position": pos(6, 13, 6, 8)},
    {"text": "## Arrivals (last 24h)", "position": pos(0, 21, 12, 2)},
    {"visualization": "Arrivals Today", "position": pos(0, 23, 3, 8)},
    {"visualization": "Avg Arrival Delay", "position": pos(3, 23, 3, 8)},
    {"visualization": "Arrival Delays", "position": pos(6, 23, 6, 8)},
    {"visualization": "Arrivals Board", "position": pos(0, 31, 12, 10)},
    {"text": "## Departures (last 24h)", "position": pos(0, 41, 12, 2)},
    {"visualization": "Departures Today", "position": pos(0, 43, 3, 8)},
    {"visualization": "Avg Departure Delay", "position": pos(3, 43, 3, 8)},
    {"visualization": "Departure Delays", "position": pos(6, 43, 6, 8)},
    {"visualization": "Departures Board", "position": pos(0, 51, 12, 10)},
    {"text": "## Scheduled", "position": pos(0, 61, 12, 2)},
    {"visualization": "Scheduled Arrivals", "position": pos(0, 63, 3, 8)},
    {"visualization": "Scheduled Departures", "position": pos(3, 63, 3, 8)},
    {"visualization": "Scheduled Arrivals Board", "position": pos(0, 71, 6, 10)},
    {"visualization": "Scheduled Departures Board", "position": pos(6, 71, 6, 10)},
    {"visualization": "Delays by Flight", "position": pos(0, 81, 12, 8)},
    {"text": "## Historical activity (10 days)", "position": pos(0, 89, 12, 2)},
    {"visualization": "Total Flights (10d)", "position": pos(0, 91, 3, 8)},
    {"visualization": "Avg Daily Flights", "position": pos(3, 91, 3, 8)},
    {"visualization": "Peak Day Volume", "position": pos(6, 91, 3, 8)},
    {"visualization": "Daily Total Flights", "position": pos(9, 91, 3, 8)},
    {"visualization": "Flights per Day", "position": pos(0, 99, 8, 8)},
    {"visualization": "Daily Avg Delay", "position": pos(8, 99, 4, 8)},
    {"visualization": "Top Airlines by Volume", "position": pos(0, 107, 6, 8)},
    {"visualization": "Daily Flight Breakdown", "position": pos(6, 107, 6, 8)},
    {"visualization": "Airline Breakdown (10d)", "position": pos(0, 115, 12, 8)},
    {
        "text": (
            "Data: [FlightAware AeroAPI](https://www.flightaware.com/commercial/aeroapi/) "
            "for LFMT (Montpellier-Méditerranée). Times shown in local timezone "
            "(Europe/Paris). Refresh **AeroAPI Feed** for live boards and "
            "**10-Day History Feed** for historical charts (AeroAPI limit: 10 days)."
        ),
        "position": pos(0, 123, 12, 3),
    },
]


if __name__ == "__main__":
    build_and_report(
        name="Montpellier Airport",
        queries=QUERIES,
        derived=DERIVED,
        widgets=WIDGETS,
    )
