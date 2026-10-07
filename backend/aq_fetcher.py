"""Air quality data fetcher and spatial interpolator using WAQI API."""

import logging
import math
import os
from typing import Any
import requests

logger = logging.getLogger(__name__)

CONSERVATIVE_FALLBACK: dict[str, Any] = {
    "aqi": 100,
    "pm25": 50.0,
    "pm10": 80.0,
    "no2": 30.0,
    "so2": 10.0,
    "co": 1.5,
}

POLLUTANT_KEYS = ["pm25", "pm10", "no2", "so2", "co"]
DEFAULT_SPECIES = {k: -1.0 for k in POLLUTANT_KEYS}


def _extract_pollutant(entry: dict[str, Any], name: str) -> float:
    """Safely extract pollutant value or return -1.0 if missing."""
    if name in entry:
        try:
            return float(entry[name])
        except (ValueError, TypeError):
            pass
    iaqi = entry.get("iaqi", {})
    if isinstance(iaqi, dict) and name in iaqi:
        val = iaqi[name].get("v") if isinstance(iaqi[name], dict) else iaqi[name]
        try:
            return float(val)
        except (ValueError, TypeError):
            pass
    return -1.0


def _parse_station(entry: dict[str, Any]) -> dict[str, Any] | None:
    """Parse raw WAQI station JSON entry into standard schema."""
    try:
        lat = float(entry["lat"])
        lon = float(entry["lon"])
        raw_aqi = entry.get("aqi", -1)
        try:
            aqi = int(float(raw_aqi))
        except (ValueError, TypeError):
            aqi = -1
        station = {
            "uid": entry.get("uid"),
            "lat": lat,
            "lon": lon,
            "aqi": aqi,
        }
        for key in POLLUTANT_KEYS:
            station[key] = _extract_pollutant(entry, key)
        return station
    except (KeyError, ValueError, TypeError):
        return None


def get_station_detail(station_uid: str | int) -> dict[str, float]:
    """Fetch individual pollutant metrics for a station feed by UID."""
    token = os.getenv("WAQI_TOKEN", "").strip()
    if not token or not station_uid:
        return DEFAULT_SPECIES.copy()

    url = f"https://api.waqi.info/feed/@{station_uid}/?token={token}"
    try:
        response = requests.get(url, timeout=5)
        if response.status_code != 200:
            logger.error("WAQI feed request failed for UID %s", station_uid)
            return DEFAULT_SPECIES.copy()
        data = response.json()
        if data.get("status") != "ok" or "data" not in data:
            return DEFAULT_SPECIES.copy()
        iaqi = data.get("data", {}).get("iaqi", {})
        return {
            key: float(iaqi[key]["v"])
            if isinstance(iaqi.get(key), dict) and "v" in iaqi[key]
            else -1.0
            for key in POLLUTANT_KEYS
        }
    except Exception as exc:
        logger.error("Error fetching WAQI feed for UID %s: %s", station_uid, exc)
        return DEFAULT_SPECIES.copy()


def get_stations_in_bounds(
    lat1: float, lon1: float, lat2: float, lon2: float
) -> list[dict[str, Any]]:
    """Fetch monitoring stations within bounding box and enrich with details."""
    token = os.getenv("WAQI_TOKEN", "").strip()
    if not token:
        logger.warning("WAQI_TOKEN is not set. Returning empty station list.")
        return []

    lat_min, lat_max = min(lat1, lat2), max(lat1, lat2)
    lon_min, lon_max = min(lon1, lon2), max(lon1, lon2)
    url = f"https://api.waqi.info/map/bounds/?token={token}&latlng={lat_min},{lon_min},{lat_max},{lon_max}"

    try:
        response = requests.get(url, timeout=5)
        if response.status_code != 200:
            return []
        data = response.json()
        if data.get("status") != "ok" or "data" not in data:
            return []

        stations = [
            st for item in data.get("data", [])
            if (st := _parse_station(item)) is not None
        ]
        # Sequential detail enrichment capped at 10 to control latency
        for st in stations[:10]:
            if st.get("uid") is not None:
                detail = get_station_detail(st["uid"])
                st.update(detail)
        return stations
    except Exception as exc:
        logger.error("Error fetching WAQI stations: %s", exc)
        return []


def _calculate_weighted_metric(
    nearby: list[tuple[float, dict[str, Any], float]], key: str
) -> float:
    """Calculate inverse-distance weighted average for a specific metric key."""
    valid_stations = [
        (w, st[key]) for _, st, w in nearby if st.get(key, -1.0) >= 0
    ]
    if not valid_stations:
        return -1.0
    w_sum = sum(w for w, _ in valid_stations)
    if w_sum <= 0:
        return -1.0
    val_sum = sum(w * val for w, val in valid_stations)
    return round(val_sum / w_sum, 2)


def estimate_aq_at_point(
    lat: float, lon: float, stations: list[dict[str, Any]]
) -> dict[str, Any]:
    """Estimate air quality at coordinates using inverse distance weighting."""
    if not stations:
        return CONSERVATIVE_FALLBACK.copy()

    in_range: list[tuple[float, dict[str, Any]]] = []
    for st in stations:
        dist = math.hypot(st["lat"] - lat, st["lon"] - lon)
        if dist <= 0.5:
            in_range.append((dist, st))

    if not in_range:
        return CONSERVATIVE_FALLBACK.copy()

    in_range.sort(key=lambda item: item[0])
    selected = in_range[:3]

    if selected[0][0] < 1e-9:
        exact = selected[0][1]
        return {k: exact[k] for k in ["aqi"] + POLLUTANT_KEYS}

    weighted = [(d, st, 1.0 / d) for d, st in selected]
    aqi_val = _calculate_weighted_metric(weighted, "aqi")
    aqi_int = round(aqi_val) if aqi_val >= 0 else 100

    result: dict[str, Any] = {"aqi": aqi_int}
    for key in POLLUTANT_KEYS:
        result[key] = _calculate_weighted_metric(weighted, key)
    return result
