"""Hourly air quality profile builder using OpenAQ API v3 measurements."""

from collections import defaultdict
from datetime import datetime, timedelta, timezone
import logging
import os
from typing import Any
import requests

logger = logging.getLogger(__name__)

# Approximate Delhi diurnal PM2.5 pattern based on published CPCB seasonal averages.
# Used as fallback only.
DELHI_FALLBACK_PROFILE: dict[int, float] = {
    0: 95.0,
    1: 88.0,
    2: 82.0,
    3: 78.0,
    4: 75.0,
    5: 80.0,
    6: 105.0,
    7: 140.0,
    8: 162.0,
    9: 148.0,
    10: 128.0,
    11: 108.0,
    12: 92.0,
    13: 85.0,
    14: 82.0,
    15: 86.0,
    16: 98.0,
    17: 125.0,
    18: 158.0,
    19: 172.0,
    20: 165.0,
    21: 148.0,
    22: 128.0,
    23: 110.0,
}


def _parse_hour_from_utc(dt_val: Any) -> int | None:
    """Extract integer hour from ISO datetime string or nested structure."""
    if isinstance(dt_val, dict):
        dt_val = dt_val.get("utc") or dt_val.get("local")
    if not dt_val or not isinstance(dt_val, str):
        return None
    try:
        clean_str = dt_val.replace("Z", "+00:00")
        return datetime.fromisoformat(clean_str).hour
    except Exception:
        try:
            return int(dt_val.split("T")[1].split(":")[0])
        except Exception:
            return None


def _find_nearest_location(
    lat: float, lon: float, headers: dict[str, str]
) -> int | None:
    """Find the nearest OpenAQ location ID monitoring PM2.5 within 25km."""
    url = "https://api.openaq.org/v3/locations"
    params = {
        "coordinates": f"{lat},{lon}",
        "radius": 25000,
        "limit": 5,
        "parameters_id": 2,
    }
    try:
        res = requests.get(url, params=params, headers=headers, timeout=8)
        if res.status_code != 200:
            return None
        results = res.json().get("results", [])
        if not results:
            return None
        valid_locs = [loc for loc in results if "distance" in loc and "id" in loc]
        if not valid_locs:
            return results[0].get("id")
        nearest = min(valid_locs, key=lambda loc: float(loc["distance"]))
        return nearest.get("id")
    except Exception as exc:
        logger.error("Error finding OpenAQ v3 location: %s", exc)
        return None


def _fetch_location_measurements(
    location_id: int, days_back: int, headers: dict[str, str]
) -> list[dict[str, Any]]:
    """Fetch PM2.5 measurements for an OpenAQ location over the past days."""
    now = datetime.now(timezone.utc)
    date_from = (now - timedelta(days=days_back)).strftime("%Y-%m-%dT00:00:00Z")
    date_to = now.strftime("%Y-%m-%dT23:59:59Z")
    url = f"https://api.openaq.org/v3/locations/{location_id}/measurements"
    params = {
        "parameters_id": 2,
        "limit": 5000,
        "date_from": date_from,
        "date_to": date_to,
    }
    try:
        res = requests.get(url, params=params, headers=headers, timeout=8)
        if res.status_code != 200:
            return []
        return res.json().get("results", [])
    except Exception as exc:
        logger.error("Error fetching OpenAQ measurements: %s", exc)
        return []


def build_hourly_profile(
    lat: float, lon: float, days_back: int = 30
) -> dict[int, float]:
    """Build a 24-hour PM2.5 diurnal profile using OpenAQ v3 or fallback."""
    api_key = os.getenv("OPENAQ_API_KEY", "").strip()
    headers = {"X-API-Key": api_key} if api_key else {}

    location_id = _find_nearest_location(lat, lon, headers)
    if not location_id:
        return DELHI_FALLBACK_PROFILE.copy()

    measurements = _fetch_location_measurements(location_id, days_back, headers)
    if not measurements:
        return DELHI_FALLBACK_PROFILE.copy()

    buckets: dict[int, list[float]] = defaultdict(list)
    for m in measurements:
        dt_val = (
            m.get("datetime_utc")
            or m.get("datetime")
            or m.get("period", {}).get("datetimeFrom", {}).get("utc")
        )
        hour = _parse_hour_from_utc(dt_val)
        val = m.get("value")
        if hour is not None and isinstance(val, (int, float)) and val >= 0:
            buckets[hour].append(float(val))

    if len(buckets) < 3:
        return DELHI_FALLBACK_PROFILE.copy()

    means = {h: sum(vals) / len(vals) for h, vals in buckets.items()}
    overall = sum(means.values()) / len(means)
    return {h: round(means.get(h, overall), 2) for h in range(24)}
