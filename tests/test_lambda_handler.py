"""Unit tests for AWS Lambda handler."""

import json
from unittest.mock import MagicMock, patch
import pytest

from backend.lambda_function import handler


def _make_event(body: dict | str | None, method: str = "POST") -> dict:
    """Helper to create API Gateway proxy event."""
    return {
        "httpMethod": method,
        "body": json.dumps(body) if isinstance(body, dict) else body,
    }


def test_options_preflight_returns_cors() -> None:
    """OPTIONS request returns 200 with CORS headers and empty body."""
    event = _make_event(None, method="OPTIONS")
    resp = handler(event)
    assert resp["statusCode"] == 200
    assert resp["headers"]["Access-Control-Allow-Origin"] == "*"
    assert resp["headers"]["Access-Control-Allow-Methods"] == "POST, OPTIONS"


def test_missing_origin_returns_400() -> None:
    """Missing 'origin' field returns 400 with field='origin'."""
    event = _make_event(
        {
            "destination": "28.5491,77.2520",
            "mode": "driving",
            "departure_time": "2026-10-08T08:00:00+05:30",
        }
    )
    resp = handler(event)
    assert resp["statusCode"] == 400
    assert resp["headers"]["Access-Control-Allow-Origin"] == "*"
    body = json.loads(resp["body"])
    assert body["field"] == "origin"


def test_missing_mode_returns_400() -> None:
    """Missing 'mode' field returns 400 with field='mode'."""
    event = _make_event(
        {
            "origin": "28.6315,77.2167",
            "destination": "28.5491,77.2520",
            "departure_time": "2026-10-08T08:00:00+05:30",
        }
    )
    resp = handler(event)
    assert resp["statusCode"] == 400
    body = json.loads(resp["body"])
    assert body["field"] == "mode"


def test_invalid_departure_time_returns_400() -> None:
    """Invalid departure_time format returns 400."""
    event = _make_event(
        {
            "origin": "28.6315,77.2167",
            "destination": "28.5491,77.2520",
            "mode": "driving",
            "departure_time": "not-a-valid-time",
        }
    )
    resp = handler(event)
    assert resp["statusCode"] == 400
    body = json.loads(resp["body"])
    assert body["field"] == "departure_time"


def test_cache_hit_returns_cached_without_routing() -> None:
    """Cache hit returns result with cached=true without calling get_routes."""
    event = _make_event(
        {
            "origin": "28.6315,77.2167",
            "destination": "28.5491,77.2520",
            "mode": "driving",
            "departure_time": "2026-10-08T08:00:00+05:30",
        }
    )
    cached_data = {
        "routes": [{"route_id": "A", "exposure_score": 50}],
        "recommendation": {"recommended_route": "A"},
        "cached": False,
    }
    with patch("backend.lambda_function.get_cached_result", return_value=cached_data):
        with patch("backend.lambda_function.get_routes") as mock_get_routes:
            resp = handler(event)
            assert resp["statusCode"] == 200
            assert resp["headers"]["Access-Control-Allow-Origin"] == "*"
            body = json.loads(resp["body"])
            assert body["cached"] is True
            assert mock_get_routes.call_count == 0


def test_cache_miss_runs_full_pipeline() -> None:
    """Cache miss runs full pipeline, stores result, and returns 200."""
    event = _make_event(
        {
            "origin": "28.6315,77.2167",
            "destination": "28.5491,77.2520",
            "mode": "driving",
            "departure_time": "2026-10-08T08:00:00+05:30",
        }
    )
    mock_routes = [
        {
            "route_id": "A",
            "distance_km": 10.0,
            "duration_min": 30.0,
            "geometry": {"type": "LineString", "coordinates": [[77.2, 28.6], [77.25, 28.55]]},
            "segments": [
                {"lat": 28.6, "lon": 77.2, "duration_min": 15.0, "congestion": 0.5},
                {"lat": 28.55, "lon": 77.25, "duration_min": 15.0, "congestion": 0.5},
            ],
        }
    ]
    with patch("backend.lambda_function.get_cached_result", return_value=None):
        with patch("backend.lambda_function.get_routes", return_value=mock_routes):
            with patch("backend.lambda_function.get_stations_in_bounds", return_value=[]):
                with patch("backend.lambda_function.get_weather", return_value={"temperature": 25.0, "humidity": 50.0}):
                    with patch("backend.lambda_function.build_hourly_profile", return_value={h: 50.0 for h in range(24)}):
                        with patch("backend.lambda_function.store_result") as mock_store:
                            resp = handler(event)
                            assert resp["statusCode"] == 200
                            body = json.loads(resp["body"])
                            assert len(body["routes"]) == 1
                            assert body["recommendation"]["recommended_route"] == "A"
                            assert mock_store.call_count == 1


def test_get_routes_empty_returns_503() -> None:
    """get_routes returning [] returns 503 routing_unavailable."""
    event = _make_event(
        {
            "origin": "28.6315,77.2167",
            "destination": "28.5491,77.2520",
            "mode": "driving",
            "departure_time": "2026-10-08T08:00:00+05:30",
        }
    )
    with patch("backend.lambda_function.get_cached_result", return_value=None):
        with patch("backend.lambda_function.get_routes", return_value=[]):
            resp = handler(event)
            assert resp["statusCode"] == 503
            body = json.loads(resp["body"])
            assert body["error"] == "routing_unavailable"


def test_unhandled_exception_returns_500() -> None:
    """Unhandled exception inside pipeline returns 500."""
    event = _make_event(
        {
            "origin": "28.6315,77.2167",
            "destination": "28.5491,77.2520",
            "mode": "driving",
            "departure_time": "2026-10-08T08:00:00+05:30",
        }
    )
    with patch("backend.lambda_function.get_cached_result", side_effect=RuntimeError("DB exploded")):
        resp = handler(event)
        assert resp["statusCode"] == 500
        assert resp["headers"]["Access-Control-Allow-Origin"] == "*"
        body = json.loads(resp["body"])
        assert body["error"] == "internal_error"
