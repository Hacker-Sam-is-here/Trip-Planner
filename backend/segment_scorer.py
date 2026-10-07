"""Segment scoring pipeline integrating weather, AQ stations, and ML inference."""

from typing import Any
from backend.aq_fetcher import estimate_aq_at_point
from backend.ml_classifier import classify_segment
from backend.models import RouteSegment


def _build_segment_features(
    congestion: float, aq: dict[str, Any], weather: dict[str, float]
) -> dict[str, float]:
    """Construct 9-feature vector for air quality classification.

    Note: The congestion -> Proximity proxy is an acknowledged approximation:
    higher traffic congestion is correlated with proximity to industrial / arterial zones.
    """
    pm25 = float(aq["pm25"]) if aq.get("pm25", -1.0) >= 0 else 50.0
    pm10 = float(aq["pm10"]) if aq.get("pm10", -1.0) >= 0 else 80.0
    no2 = float(aq["no2"]) if aq.get("no2", -1.0) >= 0 else 30.0
    so2 = float(aq["so2"]) if aq.get("so2", -1.0) >= 0 else 10.0
    co = float(aq["co"]) if aq.get("co", -1.0) >= 0 else 1.5

    proximity_to_industrial = float(congestion * 10.0)
    population_density = 500.0  # fixed default for MVP

    return {
        "Temperature": float(weather.get("temperature", 25.0)),
        "Humidity": float(weather.get("humidity", 60.0)),
        "PM2.5": pm25,
        "PM10": pm10,
        "NO2": no2,
        "SO2": so2,
        "CO": co,
        "Proximity_to_Industrial_Areas": proximity_to_industrial,
        "Population_Density": population_density,
    }


def score_route_segments(
    route: dict[str, Any],
    stations: list[dict[str, Any]],
    weather: dict[str, float],
    hour_profile: dict[int, float],
    model: Any,
    departure_hour: int,
) -> list[RouteSegment]:
    """Score individual segments of a route using environmental data and ML model."""
    scored: list[RouteSegment] = []
    for seg in route.get("segments", []):
        lat = float(seg["lat"])
        lon = float(seg["lon"])
        duration = float(seg.get("duration_min", 0.0))
        congestion = float(seg.get("congestion", 0.5))

        aq = estimate_aq_at_point(lat, lon, stations)
        features = _build_segment_features(congestion, aq, weather)
        aqi_class = classify_segment(model, features)

        scored.append(
            RouteSegment(
                lat=lat,
                lon=lon,
                aqi_class=aqi_class,
                pm25=features["PM2.5"],
                duration_min=duration,
                congestion=congestion,
            )
        )
    return scored
