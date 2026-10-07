"""Route fetching module using Mapbox Directions API."""

import logging
import os
from typing import Any
import requests

logger = logging.getLogger(__name__)

ROUTE_IDS = ["A", "B", "C", "D", "E"]

PROFILE_MAP: dict[str, str] = {
    "walking": "mapbox/walking",
    "cycling": "mapbox/cycling",
    "driving": "mapbox/driving-traffic",
}


def _format_coords(origin: str, destination: str) -> str:
    """Format 'lat,lon' origin and destination into Mapbox 'lon,lat;lon,lat' string."""
    orig_parts = [p.strip() for p in origin.split(",")]
    dest_parts = [p.strip() for p in destination.split(",")]
    return f"{orig_parts[1]},{orig_parts[0]};{dest_parts[1]},{dest_parts[0]}"


def _sample_indices(total_coords: int, target_samples: int = 12) -> list[int]:
    """Sample evenly spaced coordinate indices to get 8-15 points."""
    if total_coords <= target_samples:
        return list(range(total_coords))
    indices = [
        int(round(i * (total_coords - 1) / (target_samples - 1)))
        for i in range(target_samples)
    ]
    return sorted(list(dict.fromkeys(indices)))


def _extract_congestion(
    idx: int, congestion_array: list[Any] | None
) -> float:
    """Extract numeric congestion percentage (0.0-1.0) or default to 0.5."""
    if congestion_array and idx < len(congestion_array):
        val = congestion_array[idx]
        if isinstance(val, (int, float)):
            return max(0.0, min(1.0, float(val) / 100.0))
    return 0.5


def _extract_segments(
    geometry: dict[str, Any],
    annotations: list[Any] | None,
    total_duration_min: float,
) -> list[dict[str, Any]]:
    """Sample geometry coordinates and generate segment metadata."""
    coords = geometry.get("coordinates", [])
    indices = _sample_indices(len(coords))
    if not indices:
        return []

    seg_duration = (
        round(total_duration_min / len(indices), 2) if len(indices) > 0 else 0.0
    )
    segments: list[dict[str, Any]] = []
    for idx in indices:
        lon, lat = coords[idx][0], coords[idx][1]
        congestion = _extract_congestion(idx, annotations)
        segments.append(
            {
                "lat": float(lat),
                "lon": float(lon),
                "duration_min": seg_duration,
                "congestion": congestion,
            }
        )
    return segments


def _parse_mapbox_route(route: dict[str, Any], route_id: str) -> dict[str, Any]:
    """Parse raw Mapbox route into standardized dictionary."""
    distance_km = round(float(route.get("distance", 0.0)) / 1000.0, 2)
    duration_min = round(float(route.get("duration", 0.0)) / 60.0, 1)
    geometry = route.get("geometry", {"type": "LineString", "coordinates": []})

    legs = route.get("legs", [])
    first_leg = legs[0] if legs else {}
    annot_dict = (
        first_leg.get("annotation")
        or first_leg.get("annotations")
        or route.get("annotation")
        or {}
    )
    congestions = annot_dict.get("congestion_numeric")

    segments = _extract_segments(geometry, congestions, duration_min)
    return {
        "route_id": route_id,
        "distance_km": distance_km,
        "duration_min": duration_min,
        "geometry": geometry,
        "segments": segments,
    }


def get_routes(origin: str, destination: str, mode: str) -> list[dict[str, Any]]:
    """Fetch route alternatives from Mapbox Directions API."""
    token = os.getenv("MAPBOX_TOKEN", "").strip()
    if not token:
        logger.warning("MAPBOX_TOKEN is not set. Returning empty routes.")
        return []

    profile = PROFILE_MAP.get(mode, "mapbox/walking")
    try:
        coords_str = _format_coords(origin, destination)
    except Exception as exc:
        logger.error("Failed to parse origin/destination coordinates: %s", exc)
        return []

    url = f"https://api.mapbox.com/directions/v5/{profile}/{coords_str}"
    params = {
        "access_token": token,
        "alternatives": "true",
        "geometries": "geojson",
        "steps": "false",
        "annotations": "congestion_numeric,duration,distance",
        "overview": "full",
    }

    try:
        response = requests.get(url, params=params, timeout=8)
        if response.status_code != 200:
            logger.error("Mapbox directions request failed: HTTP %s", response.status_code)
            return []
        data = response.json()
        raw_routes = data.get("routes", [])
        return [
            _parse_mapbox_route(r, ROUTE_IDS[i] if i < len(ROUTE_IDS) else f"R{i+1}")
            for i, r in enumerate(raw_routes)
        ]
    except Exception as exc:
        logger.error("Error calling Mapbox Directions API: %s", exc)
        return []
