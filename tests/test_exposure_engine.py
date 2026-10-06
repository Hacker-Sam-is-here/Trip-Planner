"""Tests for backend.exposure_engine module."""

import pytest
from backend.exposure_engine import (
    aqi_class_to_value,
    compare_routes,
    normalize_score,
    score_route,
    score_segment,
)
from backend.models import RouteResult, RouteSegment


def test_aqi_class_to_value() -> None:
    """Verify correct numeric values for AQI classes."""
    assert aqi_class_to_value("Good") == 25
    assert aqi_class_to_value("good") == 25
    assert aqi_class_to_value("Moderate") == 50
    assert aqi_class_to_value("Poor") == 75
    assert aqi_class_to_value("Hazardous") == 100
    with pytest.raises(ValueError):
        aqi_class_to_value("Unknown")


def test_route_all_good_scores_low() -> None:
    """A route with all 'Good' segments must produce a 'Low' exposure score."""
    segments = [
        RouteSegment(lat=28.61, lon=77.20, aqi_class="Good", pm25=12.0, duration_min=10.0),
        RouteSegment(lat=28.62, lon=77.21, aqi_class="Good", pm25=14.0, duration_min=15.0),
    ]
    raw = score_route(segments, hour_profile={})
    score, label = normalize_score(raw)
    assert score == 25
    assert label == "Low"


def test_route_all_hazardous_scores_very_high() -> None:
    """A route with all 'Hazardous' segments must produce a 'Very High' exposure score."""
    segments = [
        RouteSegment(lat=28.61, lon=77.20, aqi_class="Hazardous", pm25=250.0, duration_min=20.0),
        RouteSegment(lat=28.62, lon=77.21, aqi_class="Hazardous", pm25=300.0, duration_min=10.0),
    ]
    raw = score_route(segments, hour_profile={})
    score, label = normalize_score(raw)
    assert score == 100
    assert label == "Very High"


def test_route_b_lower_than_route_a_recommendation() -> None:
    """Route B scoring lower than Route A triggers correct recommendation."""
    route_a = RouteResult(
        route_id="A",
        distance_km=8.2,
        duration_min=27.0,
        exposure_score=72,
        exposure_label="High",
        geometry={"type": "LineString", "coordinates": []},
    )
    route_b = RouteResult(
        route_id="B",
        distance_km=9.1,
        duration_min=31.0,
        exposure_score=54,
        exposure_label="Moderate",
        geometry={"type": "LineString", "coordinates": []},
    )
    rec = compare_routes([route_a, route_b])
    assert rec["recommended_route"] == "B"
    assert "lower estimated exposure" in rec["reason"]
    assert len(rec["contributing_factors"]) >= 1


def test_missing_hour_profile_defaults_to_one() -> None:
    """Missing hour_profile (empty dict or None) does not crash and defaults to 1.0."""
    segments = [
        RouteSegment(lat=28.61, lon=77.20, aqi_class="Moderate", pm25=35.0, duration_min=10.0),
    ]
    raw_empty = score_route(segments, hour_profile={})
    raw_none = score_route(segments, hour_profile=None)
    assert raw_empty == 50.0
    assert raw_none == 50.0


def test_hour_profile_with_multiplier() -> None:
    """Hour profile scaling with hourly mean and daily mean."""
    segments = [
        RouteSegment(lat=28.61, lon=77.20, aqi_class="Moderate", pm25=35.0, duration_min=10.0),
    ]
    profile = {"hour_avg_pm25": 40.0, "daily_mean_pm25": 50.0}
    raw = score_route(segments, hour_profile=profile)
    assert raw == 50.0 * 0.8  # 40.0


def test_score_segment_calculation() -> None:
    """Test score_segment with explicit hour multiplier."""
    seg = RouteSegment(lat=28.61, lon=77.20, aqi_class="Poor", pm25=60.0, duration_min=12.0)
    score = score_segment(seg, hour_multiplier=1.2)
    assert score == pytest.approx(75 * 12.0 * 1.2)


def test_normalize_score_boundaries() -> None:
    """Test exact threshold boundaries defined in AGENTS.md."""
    assert normalize_score(0.0) == (0, "Low")
    assert normalize_score(30.0) == (30, "Low")
    assert normalize_score(31.0) == (31, "Moderate")
    assert normalize_score(60.0) == (60, "Moderate")
    assert normalize_score(61.0) == (61, "High")
    assert normalize_score(80.0) == (80, "High")
    assert normalize_score(81.0) == (81, "Very High")
    assert normalize_score(100.0) == (100, "Very High")
    assert normalize_score(120.0) == (100, "Very High")


def test_compare_routes_single_and_empty() -> None:
    """Test edge cases with single route or empty route list."""
    empty_rec = compare_routes([])
    assert empty_rec["recommended_route"] == ""

    single_route = RouteResult(
        route_id="A",
        distance_km=5.0,
        duration_min=15.0,
        exposure_score=35,
        exposure_label="Moderate",
        geometry={"type": "LineString", "coordinates": []},
    )
    single_rec = compare_routes([single_route])
    assert single_rec["recommended_route"] == "A"
