"""Weather skill — current conditions, daily forecasts, and geocoding via Open-Meteo.

Pure standard library (urllib) so it runs unchanged in the alpine Python sandbox with no pip
dependencies and no credentials. Open-Meteo is keyless. `params` is injected as a global by the
Sophon runtime and carries the tool name and the tool's call arguments.

Two hosts are used:
  - https://geocoding-api.open-meteo.com  (place name -> lat/lon)
  - https://api.open-meteo.com             (forecast)
"""

import json
import urllib.request
import urllib.parse
import urllib.error

tool_name = params.get("tool", "")

GEOCODE_BASE = "https://geocoding-api.open-meteo.com/v1/search"
FORECAST_BASE = "https://api.open-meteo.com/v1/forecast"

HEADERS = {
    "Accept": "application/json",
    "User-Agent": "sophon-weather-skill",
}

# WMO weather interpretation codes -> human-readable text.
WEATHER_CODES = {
    0: "Clear sky",
    1: "Mainly clear",
    2: "Partly cloudy",
    3: "Overcast",
    45: "Fog",
    48: "Depositing rime fog",
    51: "Light drizzle",
    53: "Moderate drizzle",
    55: "Dense drizzle",
    56: "Light freezing drizzle",
    57: "Dense freezing drizzle",
    61: "Slight rain",
    63: "Moderate rain",
    65: "Heavy rain",
    66: "Light freezing rain",
    67: "Heavy freezing rain",
    71: "Slight snow fall",
    73: "Moderate snow fall",
    75: "Heavy snow fall",
    77: "Snow grains",
    80: "Slight rain showers",
    81: "Moderate rain showers",
    82: "Violent rain showers",
    85: "Slight snow showers",
    86: "Heavy snow showers",
    95: "Thunderstorm",
    96: "Thunderstorm with slight hail",
    99: "Thunderstorm with heavy hail",
}


def describe_code(code):
    try:
        return WEATHER_CODES.get(int(code), "Unknown")
    except (TypeError, ValueError):
        return "Unknown"


def request(url, query=None):
    """GET a URL with an optional query dict and return parsed JSON."""
    if query:
        clean = {k: v for k, v in query.items() if v not in (None, "")}
        if clean:
            url = f"{url}?{urllib.parse.urlencode(clean)}"
    req = urllib.request.Request(url, headers=HEADERS, method="GET")
    try:
        with urllib.request.urlopen(req) as resp:
            raw = resp.read().decode()
            return json.loads(raw) if raw else None
    except urllib.error.HTTPError as e:
        detail = e.read().decode() if e.fp else ""
        raise RuntimeError(f"Open-Meteo API error {e.code}: {detail}") from e
    except urllib.error.URLError as e:
        raise RuntimeError(f"Network error contacting Open-Meteo: {e.reason}") from e


def geocode(name):
    """Look up the first matching place for a name. Returns a dict or raises ValueError."""
    result = request(GEOCODE_BASE, query={"name": name, "count": 1})
    matches = (result or {}).get("results") or []
    if not matches:
        raise ValueError(f"no place found for location: {name}")
    top = matches[0]
    return {
        "name": top.get("name"),
        "country": top.get("country"),
        "admin1": top.get("admin1"),
        "latitude": top.get("latitude"),
        "longitude": top.get("longitude"),
    }


def resolve_coords():
    """Resolve request params into (latitude, longitude, place-dict-or-None).

    Prefers explicit latitude+longitude; otherwise geocodes params['location'].
    Raises ValueError if neither is supplied.
    """
    lat = params.get("latitude")
    lon = params.get("longitude")
    if lat is not None and lon is not None:
        try:
            return float(lat), float(lon), None
        except (TypeError, ValueError):
            raise ValueError("latitude and longitude must be numbers")
    location = params.get("location")
    if location:
        place = geocode(location)
        return float(place["latitude"]), float(place["longitude"]), place
    raise ValueError("provide 'location' or latitude+longitude")


def clamp(value, default, minimum, maximum):
    try:
        return max(minimum, min(int(value), maximum))
    except (TypeError, ValueError):
        return default


# --- Tool handlers ---------------------------------------------------------

def current():
    lat, lon, place = resolve_coords()
    result = request(FORECAST_BASE, query={
        "latitude": lat,
        "longitude": lon,
        "current": "temperature_2m,relative_humidity_2m,apparent_temperature,"
                   "precipitation,weather_code,wind_speed_10m",
        "timezone": "auto",
    })
    cur = (result or {}).get("current") or {}
    units = (result or {}).get("current_units") or {}
    code = cur.get("weather_code")
    out = {
        "latitude": (result or {}).get("latitude", lat),
        "longitude": (result or {}).get("longitude", lon),
        "timezone": (result or {}).get("timezone"),
        "time": cur.get("time"),
        "temperature": cur.get("temperature_2m"),
        "apparentTemperature": cur.get("apparent_temperature"),
        "relativeHumidity": cur.get("relative_humidity_2m"),
        "precipitation": cur.get("precipitation"),
        "windSpeed": cur.get("wind_speed_10m"),
        "weatherCode": code,
        "description": describe_code(code),
        "units": {
            "temperature": units.get("temperature_2m"),
            "apparentTemperature": units.get("apparent_temperature"),
            "relativeHumidity": units.get("relative_humidity_2m"),
            "precipitation": units.get("precipitation"),
            "windSpeed": units.get("wind_speed_10m"),
        },
    }
    if place:
        out["place"] = place
    print(json.dumps(out))


def forecast():
    lat, lon, place = resolve_coords()
    days = clamp(params.get("days", 7), 7, 1, 16)
    result = request(FORECAST_BASE, query={
        "latitude": lat,
        "longitude": lon,
        "daily": "weather_code,temperature_2m_max,temperature_2m_min,precipitation_sum",
        "forecast_days": days,
        "timezone": "auto",
    })
    daily = (result or {}).get("daily") or {}
    units = (result or {}).get("daily_units") or {}
    times = daily.get("time") or []
    codes = daily.get("weather_code") or []
    tmax = daily.get("temperature_2m_max") or []
    tmin = daily.get("temperature_2m_min") or []
    precip = daily.get("precipitation_sum") or []
    entries = []
    for i in range(len(times)):
        code = codes[i] if i < len(codes) else None
        entries.append({
            "date": times[i],
            "weatherCode": code,
            "description": describe_code(code),
            "temperatureMax": tmax[i] if i < len(tmax) else None,
            "temperatureMin": tmin[i] if i < len(tmin) else None,
            "precipitationSum": precip[i] if i < len(precip) else None,
        })
    out = {
        "latitude": (result or {}).get("latitude", lat),
        "longitude": (result or {}).get("longitude", lon),
        "timezone": (result or {}).get("timezone"),
        "days": len(entries),
        "units": {
            "temperatureMax": units.get("temperature_2m_max"),
            "temperatureMin": units.get("temperature_2m_min"),
            "precipitationSum": units.get("precipitation_sum"),
        },
        "forecast": entries,
    }
    if place:
        out["place"] = place
    print(json.dumps(out))


def geocode_search():
    name = params.get("name")
    if not name:
        raise ValueError("missing 'name'")
    count = clamp(params.get("count", 10), 10, 1, 100)
    result = request(GEOCODE_BASE, query={"name": name, "count": count})
    matches = (result or {}).get("results") or []
    out = [{
        "name": m.get("name"),
        "country": m.get("country"),
        "admin1": m.get("admin1"),
        "latitude": m.get("latitude"),
        "longitude": m.get("longitude"),
    } for m in matches]
    print(json.dumps({"count": len(out), "matches": out}))


HANDLERS = {
    "weather.current": current,
    "weather.forecast": forecast,
    "weather.geocode": geocode_search,
}

try:
    handler = HANDLERS.get(tool_name)
    if handler is None:
        print(json.dumps({"error": f"Unknown tool: {tool_name}"}))
    else:
        handler()
except (RuntimeError, ValueError) as e:
    print(json.dumps({"error": str(e)}))
except Exception as e:  # noqa: BLE001
    print(json.dumps({"error": f"Unexpected error: {type(e).__name__}: {e}"}))
