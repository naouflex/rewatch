#!/usr/bin/env python3
"""Create a parameterized France Weather dashboard with a city dropdown.

All widgets share a dashboard-level ``city`` enum parameter. Coordinates are
resolved inside each Python query from a built-in lookup table, then Open-Meteo
forecast and air-quality APIs are called for the selected city.
"""

from __future__ import annotations

from dashboard_script_utils import build_and_report, request
from rewatch.assistant import dashboard_builder

DS_PYTHON = 4
TIMEZONE = "Europe/Paris"
DEFAULT_CITY = "Paris"

CITY_ENUM_OPTIONS = "\n".join(
    [
        "Paris",
        "Montpellier",
        "Lyon",
        "Marseille",
        "Toulouse",
        "Nice",
        "Bordeaux",
        "Lille",
        "Strasbourg",
        "Nantes",
    ]
)

CITY_PARAM = {
    "name": "city",
    "title": "City",
    "type": "enum",
    "enumOptions": CITY_ENUM_OPTIONS,
    "value": DEFAULT_CITY,
}

DASHBOARD_PARAM_MAPPING = {
    "city": {
        "name": "city",
        "type": "dashboard-level",
        "mapTo": "city",
        "value": None,
        "title": "City",
    }
}

# Shared helper injected at the top of every Python query.
PY_COMMON = """
import requests
import datetime

WMO = {
    0: "Clear sky", 1: "Mainly clear", 2: "Partly cloudy", 3: "Overcast",
    45: "Fog", 48: "Rime fog",
    51: "Light drizzle", 53: "Drizzle", 55: "Dense drizzle",
    56: "Freezing drizzle", 57: "Freezing drizzle",
    61: "Light rain", 63: "Rain", 65: "Heavy rain",
    66: "Freezing rain", 67: "Freezing rain",
    71: "Light snow", 73: "Snow", 75: "Heavy snow", 77: "Snow grains",
    80: "Light showers", 81: "Showers", 82: "Violent showers",
    85: "Snow showers", 86: "Snow showers",
    95: "Thunderstorm", 96: "Thunderstorm + hail", 99: "Thunderstorm + hail",
}
EMOJI = {
    0: "\\u2600\\ufe0f", 1: "\\U0001f324\\ufe0f", 2: "\\u26c5", 3: "\\u2601\\ufe0f",
    45: "\\U0001f32b\\ufe0f", 48: "\\U0001f32b\\ufe0f",
    51: "\\U0001f326\\ufe0f", 53: "\\U0001f326\\ufe0f", 55: "\\U0001f326\\ufe0f",
    56: "\\U0001f326\\ufe0f", 57: "\\U0001f326\\ufe0f",
    61: "\\U0001f327\\ufe0f", 63: "\\U0001f327\\ufe0f", 65: "\\U0001f327\\ufe0f",
    66: "\\U0001f327\\ufe0f", 67: "\\U0001f327\\ufe0f",
    71: "\\U0001f328\\ufe0f", 73: "\\U0001f328\\ufe0f", 75: "\\U0001f328\\ufe0f",
    77: "\\U0001f328\\ufe0f",
    80: "\\U0001f326\\ufe0f", 81: "\\U0001f327\\ufe0f", 82: "\\u26c8\\ufe0f",
    85: "\\U0001f328\\ufe0f", 86: "\\U0001f328\\ufe0f",
    95: "\\u26c8\\ufe0f", 96: "\\u26c8\\ufe0f", 99: "\\u26c8\\ufe0f",
}
CITIES = {
    "Paris": (48.8566, 2.3522),
    "Montpellier": (43.6113, 3.8772),
    "Lyon": (45.7640, 4.8357),
    "Marseille": (43.2965, 5.3698),
    "Toulouse": (43.6047, 1.4442),
    "Nice": (43.7102, 7.2620),
    "Bordeaux": (44.8378, -0.5792),
    "Lille": (50.6292, 3.0573),
    "Strasbourg": (48.5734, 7.7521),
    "Nantes": (47.2184, -1.5536),
}


def describe(code, WMO=WMO, EMOJI=EMOJI):
    label = WMO.get(code, "Unknown")
    icon = EMOJI.get(code, "")
    return (icon + " " + label) if icon else label


def fetch(url, params, requests=requests):
    return requests.get(url, params=params, timeout=25).json()


city = "{{city}}"
latitude, longitude = CITIES[city]
"""

CURRENT_QUERY = PY_COMMON + """
data = fetch("https://api.open-meteo.com/v1/forecast", {
    "latitude": latitude,
    "longitude": longitude,
    "current": "temperature_2m,apparent_temperature,relative_humidity_2m,"
               "precipitation,weather_code,cloud_cover,surface_pressure,"
               "wind_speed_10m,wind_gusts_10m,wind_direction_10m,is_day",
    "daily": "uv_index_max,precipitation_probability_max,sunrise,sunset,"
             "temperature_2m_max,temperature_2m_min",
    "forecast_days": 1,
    "timezone": "%(tz)s",
})
cur = data["current"]
day = data["daily"]

result = {}
add_result_column(result, "city", "City", "string")
add_result_column(result, "conditions", "Conditions", "string")
add_result_column(result, "temperature_c", "Temperature (\\u00b0C)", "float")
add_result_column(result, "feels_like_c", "Feels Like (\\u00b0C)", "float")
add_result_column(result, "humidity_pct", "Humidity (%%)", "float")
add_result_column(result, "wind_kmh", "Wind (km/h)", "float")
add_result_column(result, "wind_gusts_kmh", "Gusts (km/h)", "float")
add_result_column(result, "pressure_hpa", "Pressure (hPa)", "float")
add_result_column(result, "cloud_cover_pct", "Cloud Cover (%%)", "float")
add_result_column(result, "uv_index_max", "UV Index (max today)", "float")
add_result_column(result, "rain_chance_today_pct", "Rain Chance Today (%%)", "float")
add_result_column(result, "today_high_c", "Today High (\\u00b0C)", "float")
add_result_column(result, "today_low_c", "Today Low (\\u00b0C)", "float")
add_result_column(result, "sunrise", "Sunrise", "string")
add_result_column(result, "sunset", "Sunset", "string")
add_result_column(result, "updated_at", "Updated", "string")
add_result_row(result, {
    "city": city,
    "conditions": describe(cur["weather_code"]),
    "temperature_c": cur["temperature_2m"],
    "feels_like_c": cur["apparent_temperature"],
    "humidity_pct": cur["relative_humidity_2m"],
    "wind_kmh": cur["wind_speed_10m"],
    "wind_gusts_kmh": cur["wind_gusts_10m"],
    "pressure_hpa": cur["surface_pressure"],
    "cloud_cover_pct": cur["cloud_cover"],
    "uv_index_max": day["uv_index_max"][0],
    "rain_chance_today_pct": day["precipitation_probability_max"][0],
    "today_high_c": day["temperature_2m_max"][0],
    "today_low_c": day["temperature_2m_min"][0],
    "sunrise": day["sunrise"][0][-5:],
    "sunset": day["sunset"][0][-5:],
    "updated_at": datetime.datetime.now().strftime("%%H:%%M %%d %%b %%Y"),
})
""" % {"tz": TIMEZONE}

HOURLY_QUERY = PY_COMMON + """
data = fetch("https://api.open-meteo.com/v1/forecast", {
    "latitude": latitude,
    "longitude": longitude,
    "hourly": "temperature_2m,apparent_temperature,precipitation_probability,"
              "precipitation,wind_speed_10m,wind_gusts_10m,relative_humidity_2m",
    "forecast_days": 3,
    "timezone": "%(tz)s",
})
hourly = data["hourly"]

result = {}
add_result_column(result, "time", "Time", "datetime")
add_result_column(result, "temperature_c", "Temperature (\\u00b0C)", "float")
add_result_column(result, "feels_like_c", "Feels Like (\\u00b0C)", "float")
add_result_column(result, "rain_chance_pct", "Rain Chance (%%)", "float")
add_result_column(result, "precipitation_mm", "Precipitation (mm)", "float")
add_result_column(result, "wind_kmh", "Wind (km/h)", "float")
add_result_column(result, "wind_gusts_kmh", "Gusts (km/h)", "float")
add_result_column(result, "humidity_pct", "Humidity (%%)", "float")

now = datetime.datetime.now()
start = now.strftime("%%Y-%%m-%%dT%%H:00")
kept = 0
for i, ts in enumerate(hourly["time"]):
    if ts < start or kept >= 48:
        continue
    kept += 1
    add_result_row(result, {
        "time": ts.replace("T", " ") + ":00",
        "temperature_c": hourly["temperature_2m"][i],
        "feels_like_c": hourly["apparent_temperature"][i],
        "rain_chance_pct": hourly["precipitation_probability"][i],
        "precipitation_mm": hourly["precipitation"][i],
        "wind_kmh": hourly["wind_speed_10m"][i],
        "wind_gusts_kmh": hourly["wind_gusts_10m"][i],
        "humidity_pct": hourly["relative_humidity_2m"][i],
    })
""" % {"tz": TIMEZONE}

DAILY_QUERY = PY_COMMON + """
data = fetch("https://api.open-meteo.com/v1/forecast", {
    "latitude": latitude,
    "longitude": longitude,
    "daily": "weather_code,temperature_2m_max,temperature_2m_min,"
             "precipitation_sum,precipitation_probability_max,"
             "wind_speed_10m_max,uv_index_max,sunrise,sunset",
    "forecast_days": 7,
    "timezone": "%(tz)s",
})
daily = data["daily"]

result = {}
add_result_column(result, "date", "Date", "date")
add_result_column(result, "day", "Day", "string")
add_result_column(result, "conditions", "Conditions", "string")
add_result_column(result, "high_c", "High (\\u00b0C)", "float")
add_result_column(result, "low_c", "Low (\\u00b0C)", "float")
add_result_column(result, "rain_chance_pct", "Rain Chance (%%)", "float")
add_result_column(result, "precipitation_mm", "Rain (mm)", "float")
add_result_column(result, "wind_max_kmh", "Max Wind (km/h)", "float")
add_result_column(result, "uv_index", "UV Index", "float")
add_result_column(result, "sunrise", "Sunrise", "string")
add_result_column(result, "sunset", "Sunset", "string")

for i, date_str in enumerate(daily["time"]):
    d = datetime.datetime.fromisoformat(date_str)
    add_result_row(result, {
        "date": date_str,
        "day": d.strftime("%%A %%d %%b"),
        "conditions": describe(daily["weather_code"][i]),
        "high_c": daily["temperature_2m_max"][i],
        "low_c": daily["temperature_2m_min"][i],
        "rain_chance_pct": daily["precipitation_probability_max"][i],
        "precipitation_mm": daily["precipitation_sum"][i],
        "wind_max_kmh": daily["wind_speed_10m_max"][i],
        "uv_index": daily["uv_index_max"][i],
        "sunrise": daily["sunrise"][i][-5:],
        "sunset": daily["sunset"][i][-5:],
    })
""" % {"tz": TIMEZONE}

AIR_QUALITY_QUERY = PY_COMMON + """
data = fetch("https://air-quality-api.open-meteo.com/v1/air-quality", {
    "latitude": latitude,
    "longitude": longitude,
    "current": "european_aqi,pm2_5,pm10,ozone,nitrogen_dioxide",
    "hourly": "european_aqi,pm2_5",
    "forecast_days": 3,
    "timezone": "%(tz)s",
})
cur = data["current"]
hourly = data["hourly"]

AQI_BANDS = [
    (20, "Good"), (40, "Fair"), (60, "Moderate"),
    (80, "Poor"), (100, "Very poor"),
]


def aqi_label(value, AQI_BANDS=AQI_BANDS):
    for limit, label in AQI_BANDS:
        if value <= limit:
            return label
    return "Extremely poor"


result = {}
add_result_column(result, "time", "Time", "datetime")
add_result_column(result, "european_aqi", "European AQI", "float")
add_result_column(result, "pm2_5", "PM2.5 (\\u00b5g/m\\u00b3)", "float")
add_result_column(result, "aqi_now", "AQI Now", "float")
add_result_column(result, "aqi_rating", "Air Quality", "string")
add_result_column(result, "pm2_5_now", "PM2.5 Now", "float")
add_result_column(result, "pm10_now", "PM10 Now", "float")
add_result_column(result, "ozone_now", "Ozone Now", "float")
add_result_column(result, "no2_now", "NO2 Now", "float")

now = datetime.datetime.now()
start = now.strftime("%%Y-%%m-%%dT%%H:00")
kept = 0
for i, ts in enumerate(hourly["time"]):
    if ts < start or kept >= 48:
        continue
    kept += 1
    add_result_row(result, {
        "time": ts.replace("T", " ") + ":00",
        "european_aqi": hourly["european_aqi"][i],
        "pm2_5": hourly["pm2_5"][i],
        "aqi_now": cur["european_aqi"],
        "aqi_rating": aqi_label(cur["european_aqi"]),
        "pm2_5_now": cur["pm2_5"],
        "pm10_now": cur["pm10"],
        "ozone_now": cur["ozone"],
        "no2_now": cur["nitrogen_dioxide"],
    })
""" % {"tz": TIMEZONE}


def counter(name: str, column: str, label: str = "") -> dict:
    return {"type": "COUNTER", "name": name, "counter_column": column, "counter_label": label}


def chart(name: str, mapping: dict, *, chart_type: str = "line") -> dict:
    return {
        "type": "CHART",
        "name": name,
        "chart_type": chart_type,
        "column_mapping": mapping,
    }


QUERIES = [
    {
        "name": "France Weather - Current Conditions",
        "description": "Live conditions for the selected French city (Open-Meteo).",
        "data_source_id": DS_PYTHON,
        "query": CURRENT_QUERY,
        "visualizations": [
            counter("Conditions Now", "conditions", "right now"),
            counter("Temperature", "temperature_c", "\u00b0C"),
            counter("Feels Like", "feels_like_c", "\u00b0C"),
            counter("Humidity", "humidity_pct", "%"),
            counter("Wind Speed", "wind_kmh", "km/h"),
            counter("Rain Chance", "rain_chance_today_pct", "% today"),
            counter("Sunrise", "sunrise", "local time"),
            counter("Sunset", "sunset", "local time"),
        ],
    },
    {
        "name": "France Weather - 48h Hourly Forecast",
        "description": "Hour-by-hour forecast for the next 48 hours (Open-Meteo).",
        "data_source_id": DS_PYTHON,
        "query": HOURLY_QUERY,
        "visualizations": [
            chart("48h Temperature", {"time": "x", "temperature_c": "y", "feels_like_c": "y"}),
            chart(
                "48h Rain Chance & Precipitation",
                {"time": "x", "rain_chance_pct": "y", "precipitation_mm": "y"},
                chart_type="column",
            ),
            chart("48h Wind", {"time": "x", "wind_kmh": "y", "wind_gusts_kmh": "y"}, chart_type="area"),
        ],
    },
    {
        "name": "France Weather - 7-Day Forecast",
        "description": "Daily outlook for the next 7 days (Open-Meteo).",
        "data_source_id": DS_PYTHON,
        "query": DAILY_QUERY,
        "visualizations": [
            chart("7-Day High & Low", {"date": "x", "high_c": "y", "low_c": "y"}),
            {"type": "TABLE", "name": "7-Day Outlook Table"},
        ],
    },
    {
        "name": "France Weather - Air Quality",
        "description": "Current and 48h air quality for the selected city (Open-Meteo).",
        "data_source_id": DS_PYTHON,
        "query": AIR_QUALITY_QUERY,
        "visualizations": [
            counter("AQI Now", "aqi_now", "European AQI"),
            counter("Air Quality Rating", "aqi_rating", "rating"),
            chart("48h AQI Forecast", {"time": "x", "european_aqi": "y"}, chart_type="area"),
            chart("48h PM2.5 Forecast", {"time": "x", "pm2_5": "y"}),
        ],
    },
]


def pos(col: int, row: int, size_x: int, size_y: int) -> dict:
    return {"col": col, "row": row, "sizeX": size_x, "sizeY": size_y}


WIDGETS = [
    {
        "text": (
            "# \U0001f30d France Weather\n\n"
            "Live conditions, 48-hour and 7-day forecast, and air quality for "
            "cities across France. Use the **City** dropdown above to switch "
            "between Paris, Montpellier, Lyon, and more \u2014 powered by "
            "[Open-Meteo](https://open-meteo.com)."
        ),
        "position": pos(0, 0, 12, 3),
    },
    {"text": "## \u2600\ufe0f Current Conditions", "position": pos(0, 3, 12, 2)},
    {"visualization": "Conditions Now", "position": pos(0, 5, 3, 4)},
    {"visualization": "Temperature", "position": pos(3, 5, 3, 4)},
    {"visualization": "Feels Like", "position": pos(6, 5, 3, 4)},
    {"visualization": "Humidity", "position": pos(9, 5, 3, 4)},
    {"visualization": "Wind Speed", "position": pos(0, 9, 3, 4)},
    {"visualization": "Rain Chance", "position": pos(3, 9, 3, 4)},
    {"visualization": "Sunrise", "position": pos(6, 9, 3, 4)},
    {"visualization": "Sunset", "position": pos(9, 9, 3, 4)},
    {"text": "## \U0001f4c8 48-Hour Forecast", "position": pos(0, 13, 12, 2)},
    {"visualization": "48h Temperature", "position": pos(0, 15, 6, 8)},
    {"visualization": "48h Rain Chance & Precipitation", "position": pos(6, 15, 6, 8)},
    {"visualization": "48h Wind", "position": pos(0, 23, 12, 8)},
    {"text": "## \U0001f4c5 7-Day Outlook", "position": pos(0, 31, 12, 2)},
    {"visualization": "7-Day High & Low", "position": pos(0, 33, 12, 8)},
    {"visualization": "7-Day Outlook Table", "position": pos(0, 41, 12, 8)},
    {"text": "## \U0001f33f Air Quality", "position": pos(0, 49, 12, 2)},
    {"visualization": "AQI Now", "position": pos(0, 51, 3, 3)},
    {"visualization": "Air Quality Rating", "position": pos(3, 51, 3, 3)},
    {"visualization": "48h AQI Forecast", "position": pos(6, 51, 6, 11)},
    {"visualization": "48h PM2.5 Forecast", "position": pos(0, 54, 6, 8)},
]


def configure_dashboard_parameters(dashboard_id: int, query_ids: list[int]) -> None:
    """Attach city parameter definitions and dashboard-level widget mappings."""
    for query_id in query_ids:
        query = request("GET", f"/api/queries/{query_id}")
        options = query.get("options") or {}
        options["parameters"] = [CITY_PARAM]
        request(
            "POST",
            f"/api/queries/{query_id}",
            body={
                "options": options,
                "version": query["version"],
                "is_draft": False,
            },
        )

    dashboard = request("GET", f"/api/dashboards/{dashboard_id}")
    options = dashboard.get("options") or {}
    options["parameters"] = [CITY_PARAM]
    options["globalParamOrder"] = ["city"]

    for widget in dashboard.get("widgets", []):
        visualization = widget.get("visualization")
        if not visualization:
            continue
        visualization_id = visualization.get("id") or widget.get("visualization_id")
        widget_options = widget.get("options") or {}
        widget_options["parameterMappings"] = DASHBOARD_PARAM_MAPPING
        request(
            "POST",
            f"/api/widgets/{widget['id']}",
            body={
                "options": widget_options,
                "dashboard_id": dashboard_id,
                "visualization_id": visualization_id,
                "text": widget.get("text") or "",
            },
        )

    request(
        "POST",
        f"/api/dashboards/{dashboard_id}",
        body={
            "options": options,
            "version": dashboard["version"],
            "is_draft": False,
        },
    )


def refresh_queries(query_ids: list[int], city: str = DEFAULT_CITY) -> None:
    import time

    for query_id in query_ids:
        request(
            "POST",
            f"/api/queries/{query_id}/results",
            body={"parameters": {"city": city}, "max_age": 0},
        )
        time.sleep(2)


def _run_adhoc_query_with_city(request_fn, query_text, data_source_id, *, timeout_seconds=120):
    """Validate parameterized queries using the default city."""
    import time

    deadline = time.monotonic() + timeout_seconds
    response = request_fn(
        "POST",
        "/api/query_results",
        body={
            "query": query_text,
            "data_source_id": data_source_id,
            "max_age": 0,
            "parameters": {"city": DEFAULT_CITY},
            "apply_auto_limit": True,
        },
    )
    if isinstance(response, dict) and "job" in response:
        result_id = dashboard_builder._poll_job(request_fn, dict(response["job"]), deadline)
        response = request_fn("GET", f"/api/query_results/{result_id}")
    return dashboard_builder._extract_result(response)


if __name__ == "__main__":
    dashboard_builder.run_adhoc_query = _run_adhoc_query_with_city
    result = build_and_report(
        name="France Weather",
        queries=QUERIES,
        widgets=WIDGETS,
    )
    query_ids = [entry["query_id"] for entry in result["queries"]]
    configure_dashboard_parameters(result["dashboard_id"], query_ids)
    refresh_queries(query_ids, DEFAULT_CITY)
    print(f"City parameter configured on queries {query_ids}")
    print("Default city: Paris — change via dashboard dropdown or ?p_city=Lyon")
