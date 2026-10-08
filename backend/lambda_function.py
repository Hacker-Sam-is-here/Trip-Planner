"""AWS Lambda handler entry point for PATHwise route analysis."""

from datetime import datetime
import json
import logging
import os
from pathlib import Path
import shutil
import traceback
from typing import Any
import boto3

from backend.aq_fetcher import get_stations_in_bounds
from backend.dynamo_cache import get_cached_result, make_cache_key, store_result
from backend.exposure_engine import compare_routes, normalize_score, score_route
from backend.ml_classifier import load_model
from backend.models import AnalysisResult, RouteResult
from backend.route_fetcher import get_routes
from backend.segment_scorer import score_route_segments
from backend.time_profile import build_hourly_profile
from backend.weather_fetcher import get_weather

logger = logging.getLogger(__name__)

CORS_HEADERS: dict[str, str] = {
    "Access-Control-Allow-Origin": "*",
    "Access-Control-Allow-Headers": "Content-Type",
    "Access-Control-Allow-Methods": "POST, OPTIONS",
}

_LOADED_MODEL: Any = None
_CACHED_HOURLY_PROFILE: dict[int, float] | None = None


def _format_response(status_code: int, body_dict: dict[str, Any]) -> dict[str, Any]:
    """Format API Gateway proxy response with CORS headers."""
    return {
        "statusCode": status_code,
        "headers": CORS_HEADERS.copy(),
        "body": json.dumps(body_dict),
    }


def _parse_request(event: dict[str, Any]) -> tuple[dict[str, Any] | None, dict[str, Any] | None]:
    """Parse and validate request body from event."""
    body_raw = event.get("body", "{}")
    if isinstance(body_raw, str):
        try:
            body = json.loads(body_raw or "{}")
        except json.JSONDecodeError:
            return None, _format_response(400, {"error": "invalid_json"})
    elif isinstance(body_raw, dict):
        body = body_raw
    else:
        body = {}

    for required_field in ["origin", "destination", "mode", "departure_time"]:
        if not body.get(required_field):
            return None, _format_response(
                400, {"error": "missing_field", "field": required_field}
            )
    return body, None


def _parse_departure_hour(departure_time: str) -> int | None:
    """Parse ISO 8601 departure time into integer hour (0-23)."""
    try:
        clean = departure_time.replace("Z", "+00:00")
        return datetime.fromisoformat(clean).hour
    except Exception:
        return None


def _get_or_load_model() -> Any:
    """Retrieve cached model or load from /tmp or S3."""
    global _LOADED_MODEL
    if _LOADED_MODEL is not None:
        return _LOADED_MODEL

    tmp_path = Path("/tmp/model.pkl")
    if not tmp_path.exists():
        bucket = os.getenv("S3_BUCKET", "").strip()
        key = os.getenv("S3_MODEL_KEY", "models/air_quality_model.pkl").strip()
        if bucket:
            try:
                s3 = boto3.client("s3")
                s3.download_file(bucket, key, str(tmp_path))
            except Exception as exc:
                logger.warning("Could not download model from S3 (%s): %s", key, exc)

    local_fallback = Path(__file__).resolve().parent.parent / "ml" / "air_quality_model.pkl"
    if not tmp_path.exists() and local_fallback.exists():
        tmp_path.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(local_fallback, tmp_path)

    path_to_use = str(tmp_path) if tmp_path.exists() else str(local_fallback)
    _LOADED_MODEL = load_model(path_to_use)
    return _LOADED_MODEL


def _get_cached_hourly_profile(lat: float, lon: float) -> dict[int, float]:
    """Retrieve cached 24h profile across warm invocations."""
    global _CACHED_HOURLY_PROFILE
    if _CACHED_HOURLY_PROFILE is None:
        _CACHED_HOURLY_PROFILE = build_hourly_profile(lat, lon)
    return _CACHED_HOURLY_PROFILE


def _compute_bounding_box(routes: list[dict[str, Any]]) -> tuple[float, float, float, float]:
    """Compute bounding box covering all route geometries with 0.1 deg padding."""
    all_lons = [c[0] for r in routes for c in r.get("geometry", {}).get("coordinates", [])]
    all_lats = [c[1] for r in routes for c in r.get("geometry", {}).get("coordinates", [])]
    return (
        min(all_lats) - 0.1,
        min(all_lons) - 0.1,
        max(all_lats) + 0.1,
        max(all_lons) + 0.1,
    )


def _build_recommended_time_profile(
    rec_route: dict[str, Any],
    stations: list[dict[str, Any]],
    weather: dict[str, float],
    hour_profile: dict[int, float],
    model: Any,
    daily_mean: float,
) -> dict[str, Any]:
    """Calculate hourly exposure scores (hours 7-19) for recommended route."""
    hours = list(range(7, 20))
    scores: list[int] = []
    for h in hours:
        h_avg = hour_profile.get(h, 50.0)
        h_profile = {"hour_avg_pm25": h_avg, "daily_mean_pm25": daily_mean}
        segs = score_route_segments(rec_route, stations, weather, hour_profile, model, h)
        raw_score = score_route(segs, h_profile)
        score, _ = normalize_score(raw_score)
        scores.append(score)
    return {
        "route": rec_route.get("route_id", "A"),
        "hours": hours,
        "scores": scores,
    }


def _score_all_routes(
    routes: list[dict[str, Any]],
    stations: list[dict[str, Any]],
    weather: dict[str, float],
    hour_profile: dict[int, float],
    model: Any,
    hour: int,
    daily_mean: float,
) -> list[RouteResult]:
    """Score all routes and return RouteResult list."""
    hour_avg = hour_profile.get(hour, 50.0)
    profile_dict = {"hour_avg_pm25": hour_avg, "daily_mean_pm25": daily_mean}
    results: list[RouteResult] = []
    for r in routes:
        segs = score_route_segments(r, stations, weather, hour_profile, model, hour)
        raw_score = score_route(segs, profile_dict)
        score, label = normalize_score(raw_score)
        results.append(
            RouteResult(
                route_id=r["route_id"],
                distance_km=r["distance_km"],
                duration_min=r["duration_min"],
                exposure_score=score,
                exposure_label=label,
                geometry=r["geometry"],
            )
        )
    return results


def _execute_analysis(
    origin: str, destination: str, mode: str, hour: int
) -> dict[str, Any] | None:
    """Execute complete routing, environmental ingestion, and scoring pipeline."""
    routes = get_routes(origin, destination, mode)
    if not routes:
        return None

    lat_min, lon_min, lat_max, lon_max = _compute_bounding_box(routes)
    stations = get_stations_in_bounds(lat_min, lon_min, lat_max, lon_max)

    first_coords = routes[0]["geometry"]["coordinates"]
    mid_coord = first_coords[len(first_coords) // 2]
    mid_lon, mid_lat = mid_coord[0], mid_coord[1]

    weather = get_weather(mid_lat, mid_lon)
    hour_profile = _get_cached_hourly_profile(mid_lat, mid_lon)
    model = _get_or_load_model()
    daily_mean = sum(hour_profile.values()) / 24.0

    route_results = _score_all_routes(
        routes, stations, weather, hour_profile, model, hour, daily_mean
    )
    recommendation = compare_routes(route_results)
    rec_id = recommendation["recommended_route"]
    rec_route = next((r for r in routes if r["route_id"] == rec_id), routes[0])
    time_profile_data = _build_recommended_time_profile(
        rec_route, stations, weather, hour_profile, model, daily_mean
    )

    analysis = AnalysisResult(
        routes=route_results,
        recommendation=recommendation,
        time_profile=time_profile_data,
        cached=False,
    )
    return analysis.to_dict()


def handler(event: dict[str, Any], context: Any = None) -> dict[str, Any]:
    """Lambda function entry point for POST /analyze-route."""
    if event.get("httpMethod") == "OPTIONS":
        return _format_response(200, {})

    try:
        body, err_resp = _parse_request(event)
        if err_resp:
            return err_resp
        assert body is not None

        hour = _parse_departure_hour(body["departure_time"])
        if hour is None:
            return _format_response(
                400, {"error": "invalid_departure_time", "field": "departure_time"}
            )

        cache_key = make_cache_key(
            body["origin"], body["destination"], body["mode"], hour
        )
        cached = get_cached_result(cache_key)
        if cached:
            cached["cached"] = True
            return _format_response(200, cached)

        result_dict = _execute_analysis(
            body["origin"], body["destination"], body["mode"], hour
        )
        if result_dict is None:
            return _format_response(503, {"error": "routing_unavailable"})

        store_result(cache_key, result_dict, ttl_hours=1)
        return _format_response(200, result_dict)
    except Exception as exc:
        logger.error("Unhandled exception in Lambda handler:\n%s", traceback.format_exc())
        return _format_response(500, {"error": "internal_error", "message": str(exc)})
