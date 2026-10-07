"""Weather data fetcher using OpenWeatherMap API."""

import logging
import os
from typing import Any
import requests

logger = logging.getLogger(__name__)

FALLBACK_WEATHER: dict[str, float] = {
    "temperature": 25.0,
    "humidity": 60.0,
    "wind_speed": 2.0,
    "wind_deg": 0.0,
}


def _parse_weather_response(data: dict[str, Any]) -> dict[str, float]:
    """Extract and validate weather metrics from API response payload."""
    main = data.get("main", {})
    wind = data.get("wind", {})
    return {
        "temperature": float(main["temp"]),
        "humidity": float(main["humidity"]),
        "wind_speed": float(wind.get("speed", 0.0)),
        "wind_deg": float(wind.get("deg", 0.0)),
    }


def get_weather(lat: float, lon: float) -> dict[str, float]:
    """Fetch current weather metrics for given coordinates or return fallback."""
    api_key = os.getenv("OWM_API_KEY", "").strip()
    if not api_key:
        logger.warning("OWM_API_KEY is not set. Returning fallback weather data.")
        return FALLBACK_WEATHER.copy()

    url = "https://api.openweathermap.org/data/2.5/weather"
    params = {"lat": lat, "lon": lon, "appid": api_key, "units": "metric"}

    try:
        response = requests.get(url, params=params, timeout=5)
        if response.status_code != 200:
            logger.error("OpenWeatherMap request failed: HTTP %s", response.status_code)
            return FALLBACK_WEATHER.copy()
        return _parse_weather_response(response.json())
    except Exception as exc:
        logger.error("Error fetching weather data from OpenWeatherMap: %s", exc)
        return FALLBACK_WEATHER.copy()
