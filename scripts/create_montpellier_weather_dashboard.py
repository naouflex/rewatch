#!/usr/bin/env python3
"""Create the Montpellier Weather dashboard from live Open-Meteo data.

Thin declarative spec on top of rewatch.assistant.dashboard_builder. All
queries run on the Python data source (id 4) and call the free Open-Meteo
forecast + air quality APIs, so every refresh pulls live data.
"""

from __future__ import annotations

from dashboard_script_utils import build_and_report

DS_PYTHON = 4

LATITUDE = 43.6113
LONGITUDE = 3.8772
TIMEZONE = "Europe/Paris"

COLORS = {
    "temperature": "#FF7230",
    "feels_like": "#FAB005",
    "rain": "#15AABF",
    "precip": "#4263EB",
    "wind": "#12B886",
    "gusts": "#0CA678",
    "t_max": "#FA5252",
    "t_min": "#339AF0",
    "aqi": "#7950F2",
    "pm25": "#E64980",
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


# The Python runner execs queries with separate globals/locals, so top-level
# names are invisible inside functions; bind them as default arguments.
def describe(code, WMO=WMO, EMOJI=EMOJI):
    label = WMO.get(code, "Unknown")
    icon = EMOJI.get(code, "")
    return (icon + " " + label) if icon else label


def fetch(url, params, requests=requests):
    return requests.get(url, params=params, timeout=25).json()
"""

CURRENT_QUERY = PY_COMMON + """
data = fetch("https://api.open-meteo.com/v1/forecast", {
    "latitude": %(lat)s,
    "longitude": %(lon)s,
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
    "updated_at": cur["time"].replace("T", " "),
})
""" % {"lat": LATITUDE, "lon": LONGITUDE, "tz": TIMEZONE}

HOURLY_QUERY = PY_COMMON + """
data = fetch("https://api.open-meteo.com/v1/forecast", {
    "latitude": %(lat)s,
    "longitude": %(lon)s,
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
""" % {"lat": LATITUDE, "lon": LONGITUDE, "tz": TIMEZONE}

DAILY_QUERY = PY_COMMON + """
data = fetch("https://api.open-meteo.com/v1/forecast", {
    "latitude": %(lat)s,
    "longitude": %(lon)s,
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
""" % {"lat": LATITUDE, "lon": LONGITUDE, "tz": TIMEZONE}

AIR_QUALITY_QUERY = PY_COMMON + """
data = fetch("https://air-quality-api.open-meteo.com/v1/air-quality", {
    "latitude": %(lat)s,
    "longitude": %(lon)s,
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
""" % {"lat": LATITUDE, "lon": LONGITUDE, "tz": TIMEZONE}


def counter(name: str, column: str, label: str = "") -> dict:
    return {"type": "COUNTER", "name": name, "counter_column": column, "counter_label": label}


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
        "key": "current",
        "name": "Montpellier Weather - Current Conditions",
        "description": "Live conditions in Montpellier from the Open-Meteo API.",
        "data_source_id": DS_PYTHON,
        "query": CURRENT_QUERY,
        "visualizations": [
            counter("Conditions Now", "conditions", "right now"),
            counter("Temperature", "temperature_c", "\u00b0C"),
            counter("Feels Like", "feels_like_c", "\u00b0C"),
            counter("Humidity", "humidity_pct", "%"),
            counter("Wind", "wind_kmh", "km/h"),
            counter("Rain Chance Today", "rain_chance_today_pct", "%"),
            counter("UV Index", "uv_index_max", "max today"),
            counter("Sunrise", "sunrise", "local time"),
            counter("Sunset", "sunset", "local time"),
        ],
    },
    {
        "key": "hourly",
        "name": "Montpellier Weather - 48h Hourly Forecast",
        "description": "Hour-by-hour forecast for the next 48 hours from Open-Meteo.",
        "data_source_id": DS_PYTHON,
        "query": HOURLY_QUERY,
        "visualizations": [
            multi_line_chart(
                "Temperature Next 48h",
                {"time": "x", "temperature_c": "y", "feels_like_c": "y"},
                {
                    "temperature_c": {"name": "Temperature", "color": COLORS["temperature"], "type": "line"},
                    "feels_like_c": {"name": "Feels like", "color": COLORS["feels_like"], "type": "line"},
                },
            ),
            multi_line_chart(
                "Rain Next 48h",
                {"time": "x", "rain_chance_pct": "y", "precipitation_mm": "y"},
                {
                    "rain_chance_pct": {"name": "Rain chance (%)", "color": COLORS["rain"], "type": "column"},
                    "precipitation_mm": {"name": "Precipitation (mm)", "color": COLORS["precip"], "type": "line"},
                },
                chart_type="column",
            ),
            multi_line_chart(
                "Wind Next 48h",
                {"time": "x", "wind_kmh": "y", "wind_gusts_kmh": "y"},
                {
                    "wind_kmh": {"name": "Wind", "color": COLORS["wind"], "type": "area"},
                    "wind_gusts_kmh": {"name": "Gusts", "color": COLORS["gusts"], "type": "line"},
                },
                chart_type="area",
            ),
        ],
    },
    {
        "key": "daily",
        "name": "Montpellier Weather - 7-Day Forecast",
        "description": "Daily outlook for the next 7 days from Open-Meteo.",
        "data_source_id": DS_PYTHON,
        "query": DAILY_QUERY,
        "visualizations": [
            multi_line_chart(
                "7-Day Temperature Range",
                {"date": "x", "high_c": "y", "low_c": "y"},
                {
                    "high_c": {"name": "High", "color": COLORS["t_max"], "type": "line"},
                    "low_c": {"name": "Low", "color": COLORS["t_min"], "type": "line"},
                },
            ),
            multi_line_chart(
                "7-Day Rain Outlook",
                {"date": "x", "precipitation_mm": "y", "rain_chance_pct": "y"},
                {
                    "precipitation_mm": {"name": "Rain (mm)", "color": COLORS["precip"], "type": "column"},
                    "rain_chance_pct": {"name": "Rain chance (%)", "color": COLORS["rain"], "type": "line"},
                },
                chart_type="column",
            ),
            {"type": "TABLE", "name": "7-Day Forecast Details"},
        ],
    },
    {
        "key": "air",
        "name": "Montpellier Weather - Air Quality",
        "description": "Current and 48h air quality (European AQI) from Open-Meteo.",
        "data_source_id": DS_PYTHON,
        "query": AIR_QUALITY_QUERY,
        "visualizations": [
            counter("European AQI", "aqi_now", "lower is better"),
            counter("Air Rating", "aqi_rating", "European AQI band"),
            counter("PM2.5", "pm2_5_now", "\u00b5g/m\u00b3"),
            counter("Ozone", "ozone_now", "\u00b5g/m\u00b3"),
            multi_line_chart(
                "Air Quality Next 48h",
                {"time": "x", "european_aqi": "y", "pm2_5": "y"},
                {
                    "european_aqi": {"name": "European AQI", "color": COLORS["aqi"], "type": "line"},
                    "pm2_5": {"name": "PM2.5", "color": COLORS["pm25"], "type": "line"},
                },
            ),
        ],
    },
]


def pos(col: int, row: int, size_x: int, size_y: int) -> dict:
    return {"col": col, "row": row, "sizeX": size_x, "sizeY": size_y}


WIDGETS = [
    {
        "text": (
            "# \u26c5 Montpellier Weather\n\n"
            "Live conditions, 48-hour and 7-day forecast, and air quality for "
            "Montpellier, France (43.61\u00b0N, 3.88\u00b0E) \u2014 powered by "
            "[Open-Meteo](https://open-meteo.com). Refresh any query to pull the latest data."
        ),
        "position": pos(0, 0, 12, 3),
    },
    {"text": "## Right Now", "position": pos(0, 3, 12, 2)},
    {"visualization": "Conditions Now", "position": pos(0, 5, 3, 8)},
    {"visualization": "Temperature", "position": pos(3, 5, 3, 8)},
    {"visualization": "Feels Like", "position": pos(6, 5, 3, 8)},
    {"visualization": "Humidity", "position": pos(9, 5, 3, 8)},
    {"visualization": "Wind", "position": pos(0, 13, 3, 8)},
    {"visualization": "Rain Chance Today", "position": pos(3, 13, 3, 8)},
    {"visualization": "Sunrise", "position": pos(6, 13, 3, 8)},
    {"visualization": "Sunset", "position": pos(9, 13, 3, 8)},
    {"text": "## Next 48 Hours", "position": pos(0, 21, 12, 2)},
    {"visualization": "Temperature Next 48h", "position": pos(0, 23, 6, 8)},
    {"visualization": "Rain Next 48h", "position": pos(6, 23, 6, 8)},
    {"visualization": "Wind Next 48h", "position": pos(0, 31, 12, 6)},
    {"text": "## 7-Day Outlook", "position": pos(0, 37, 12, 2)},
    {"visualization": "7-Day Temperature Range", "position": pos(0, 39, 6, 8)},
    {"visualization": "7-Day Rain Outlook", "position": pos(6, 39, 6, 8)},
    {"visualization": "7-Day Forecast Details", "position": pos(0, 47, 12, 8)},
    {"text": "## Air Quality", "position": pos(0, 55, 12, 2)},
    {"visualization": "European AQI", "position": pos(0, 57, 3, 8)},
    {"visualization": "Air Rating", "position": pos(3, 57, 3, 8)},
    {"visualization": "PM2.5", "position": pos(6, 57, 3, 8)},
    {"visualization": "Ozone", "position": pos(9, 57, 3, 8)},
    {"visualization": "Air Quality Next 48h", "position": pos(0, 65, 12, 6)},
    {"visualization": "UV Index", "position": pos(0, 71, 3, 8)},
    {
        "text": (
            "Data: [Open-Meteo](https://open-meteo.com) forecast and air quality APIs "
            "(free, no key). All times are Europe/Paris local time. UV, sunrise/sunset "
            "and rain chance are for the current day."
        ),
        "position": pos(3, 71, 9, 8),
    },
]


if __name__ == "__main__":
    build_and_report(
        name="Montpellier Weather",
        queries=QUERIES,
        widgets=WIDGETS,
    )
