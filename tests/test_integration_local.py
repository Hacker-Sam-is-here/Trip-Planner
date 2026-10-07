"""Local integration test for end-to-end PATHwise pipeline."""

import json
import os
from pathlib import Path
from dotenv import load_dotenv
import pytest

from backend.aq_fetcher import get_stations_in_bounds
from backend.exposure_engine import compare_routes, normalize_score, score_route
from backend.ml_classifier import load_model
from backend.models import AnalysisResult, RouteResult
from backend.route_fetcher import get_routes
from backend.segment_scorer import score_route_segments
from backend.time_profile import build_hourly_profile
from backend.weather_fetcher import get_weather

pytestmark = pytest.mark.skipif(
    not os.getenv("RUN_INTEGRATION"),
    reason="requires live API keys",
)


def _assert_no_none(data: object, path: str = "root") -> None:
    """Recursively assert that no dictionary or list value is None."""
    assert data is not None, f"Field at {path} is None"
    if isinstance(data, dict):
        for k, v in data.items():
            _assert_no_none(v, f"{path}.{k}")
    elif isinstance(data, list):
        for idx, item in enumerate(data):
            _assert_no_none(item, f"{path}[{idx}]")


def test_full_pipeline_demo_scenario() -> None:
    """Execute end-to-end demo scenario (Connaught Place to Nehru Place, Delhi)."""
    env_file = Path(__file__).resolve().parent.parent / ".env"
    if env_file.exists():
        load_dotenv(dotenv_path=env_file)

    origin = "28.6315,77.2167"
    destination = "28.5491,77.2520"
    mode = "driving"
    hour = 8

    orig_lat, orig_lon = 28.6315, 77.2167
    dest_lat, dest_lon = 28.5491, 77.2520

    routes_data = get_routes(origin, destination, mode)
    assert len(routes_data) >= 1, "At least 1 route must be returned by get_routes"

    lat_min, lat_max = min(orig_lat, dest_lat) - 0.1, max(orig_lat, dest_lat) + 0.1
    lon_min, lon_max = min(orig_lon, dest_lon) - 0.1, max(orig_lon, dest_lon) + 0.1
    stations = get_stations_in_bounds(lat_min, lon_min, lat_max, lon_max)

    weather = get_weather(orig_lat, orig_lon)
    hour_profile = build_hourly_profile(orig_lat, orig_lon)

    model_path = Path(__file__).resolve().parent.parent / "ml" / "air_quality_model.pkl"
    model = load_model(str(model_path))

    route_results: list[RouteResult] = []
    daily_mean = sum(hour_profile.values()) / 24.0
    hour_avg = hour_profile.get(hour, 50.0)
    profile_dict = {"hour_avg_pm25": hour_avg, "daily_mean_pm25": daily_mean}

    for r in routes_data:
        segments = score_route_segments(
            route=r,
            stations=stations,
            weather=weather,
            hour_profile=hour_profile,
            model=model,
            departure_hour=hour,
        )
        raw_score = score_route(segments, hour_profile=profile_dict)
        score, label = normalize_score(raw_score)
        route_results.append(
            RouteResult(
                route_id=r["route_id"],
                distance_km=r["distance_km"],
                duration_min=r["duration_min"],
                exposure_score=score,
                exposure_label=label,
                geometry=r["geometry"],
            )
        )

    recommendation = compare_routes(route_results)
    rec_route_id = recommendation["recommended_route"]

    sample_hours = [7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19]
    time_profile_data = {
        "route": rec_route_id,
        "hours": sample_hours,
        "scores": [round(hour_profile.get(h, 50.0)) for h in sample_hours],
    }

    result = AnalysisResult(
        routes=route_results,
        recommendation=recommendation,
        time_profile=time_profile_data,
        cached=False,
    )

    result_dict = result.to_dict()
    print("\n=== PIPELINE DEMO RESULT ===")
    print(json.dumps(result_dict, indent=2))

    assert len(result_dict["routes"]) >= 1
    for rt in result_dict["routes"]:
        assert 0 <= rt["exposure_score"] <= 100
        assert rt["exposure_label"] in {"Low", "Moderate", "High", "Very High"}

    valid_route_ids = [rt["route_id"] for rt in result_dict["routes"]]
    assert result_dict["recommendation"]["recommended_route"] in valid_route_ids
    _assert_no_none(result_dict)
