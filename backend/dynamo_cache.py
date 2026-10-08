"""DynamoDB caching layer for PATHwise route analysis results."""

import hashlib
import json
import logging
import os
import time
from typing import Any
import boto3
from backend.time_profile import DELHI_FALLBACK_PROFILE

logger = logging.getLogger(__name__)

_LOCAL_CACHE: dict[str, tuple[dict[str, Any], int]] = {}


def make_cache_key(origin: str, destination: str, mode: str, hour: int) -> str:
    """Generate 32-character SHA256 hex digest cache key."""
    raw = f"{origin}|{destination}|{mode}|{hour}"
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:32]


def _get_table() -> Any:
    """Retrieve DynamoDB table resource from environment configuration."""
    table_name = os.getenv("DYNAMO_TABLE", "pathwise-route-cache").strip()
    dynamodb = boto3.resource("dynamodb")
    return dynamodb.Table(table_name)


def get_cached_result(cache_key: str) -> dict[str, Any] | None:
    """Retrieve analysis result from DynamoDB if present and not expired."""
    try:
        table = _get_table()
        resp = table.get_item(Key={"cache_key": cache_key})
        item = resp.get("Item")
        if item and int(item.get("expires_at", 0)) >= int(time.time()):
            payload = item.get("payload")
            return json.loads(payload) if isinstance(payload, str) else item.get("result")
    except Exception as exc:
        logger.debug("DynamoDB query failed, checking fallback: %s", exc)

    if cache_key in _LOCAL_CACHE:
        val, exp = _LOCAL_CACHE[cache_key]
        if exp >= int(time.time()):
            return json.loads(json.dumps(val))
    return None


def store_result(
    cache_key: str, result: dict[str, Any], ttl_hours: int = 1
) -> None:
    """Store analysis result into DynamoDB with TTL expiration."""
    expires_at = int(time.time()) + ttl_hours * 3600
    _LOCAL_CACHE[cache_key] = (result, expires_at)
    try:
        table = _get_table()
        table.put_item(
            Item={
                "cache_key": cache_key,
                "payload": json.dumps(result),
                "expires_at": expires_at,
            }
        )
    except Exception as exc:
        logger.debug("DynamoDB put failed, stored in fallback: %s", exc)


def _get_demo_routes() -> list[dict[str, Any]]:
    """Return hardcoded Route A and Route B driving definitions."""
    return [
        {
            "route_id": "A",
            "distance_km": 13.44,
            "duration_min": 40.2,
            "exposure_score": 68,
            "exposure_label": "High",
            "geometry": {
                "type": "LineString",
                "coordinates": [[77.2167, 28.6315], [77.2520, 28.5491]],
            },
            "contributing_factors": [],
        },
        {
            "route_id": "B",
            "distance_km": 13.95,
            "duration_min": 41.5,
            "exposure_score": 51,
            "exposure_label": "Moderate",
            "geometry": {
                "type": "LineString",
                "coordinates": [
                    [77.2167, 28.6315],
                    [77.2400, 28.5800],
                    [77.2520, 28.5491],
                ],
            },
            "contributing_factors": [],
        },
    ]


def _build_demo_scenario_payload() -> dict[str, Any]:
    """Build the pre-computed driving demo result for Connaught Place to Nehru Place."""
    demo_hours = [7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19]
    return {
        "routes": _get_demo_routes(),
        "recommendation": {
            "recommended_route": "B",
            "reason": "Route B has ~25% lower estimated exposure despite taking 1 minute longer.",
            "contributing_factors": [
                {"factor": "traffic_density", "label": "Lower traffic near destination"},
                {"factor": "pm25", "label": "Reduced PM2.5 along Route B"},
                {"factor": "travel_time", "label": "Shorter outdoor exposure window"},
            ],
        },
        "time_profile": {
            "route": "B",
            "hours": demo_hours,
            "scores": [round(DELHI_FALLBACK_PROFILE[h]) for h in demo_hours],
        },
        "cached": True,
    }


def store_demo_scenario() -> None:
    """Store permanent demo scenario into DynamoDB with no expiry."""
    cache_key = make_cache_key("28.6315,77.2167", "28.5491,77.2520", "driving", 8)
    demo_result = _build_demo_scenario_payload()
    _LOCAL_CACHE[cache_key] = (demo_result, 9999999999)
    try:
        table = _get_table()
        table.put_item(
            Item={
                "cache_key": cache_key,
                "payload": json.dumps(demo_result),
                "expires_at": 9999999999,
            }
        )
        logger.info("Successfully stored permanent demo scenario (key: %s)", cache_key)
    except Exception as exc:
        logger.debug("Demo scenario stored in local cache fallback: %s", exc)


# Seed demo scenario in memory on module load
store_demo_scenario()

if __name__ == "__main__":
    store_demo_scenario()
