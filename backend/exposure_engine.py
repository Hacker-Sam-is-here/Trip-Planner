"""Core pollution exposure calculation engine for PATHwise."""

from typing import Any

from backend.models import RouteResult, RouteSegment

AQI_CLASS_VALUES: dict[str, int] = {
    "Good": 25,
    "Moderate": 50,
    "Poor": 75,
    "Hazardous": 100,
}


def aqi_class_to_value(label: str) -> int:
    """Map air quality class string to its defined numeric value."""
    normalized = label.strip().capitalize()
    if normalized not in AQI_CLASS_VALUES:
        raise ValueError(
            f"Unknown AQI class: '{label}'. Expected one of {list(AQI_CLASS_VALUES.keys())}"
        )
    return AQI_CLASS_VALUES[normalized]


def score_segment(segment: RouteSegment, hour_multiplier: float = 1.0) -> float:
    """Calculate the time-weighted exposure score for a single segment."""
    base_val = aqi_class_to_value(segment.aqi_class)
    segment_score = base_val * segment.duration_min
    return segment_score * hour_multiplier


def _extract_hour_multiplier(hour_profile: dict[str, Any] | None) -> float:
    """Extract or calculate the hourly adjustment multiplier from profile dict."""
    if not hour_profile:
        return 1.0
    if "multiplier" in hour_profile and isinstance(
        hour_profile["multiplier"], (int, float)
    ):
        return float(hour_profile["multiplier"])
    hour_avg = hour_profile.get("hour_avg_pm25")
    daily_mean = hour_profile.get("daily_mean_pm25")
    if (
        hour_avg is not None
        and daily_mean is not None
        and float(daily_mean) > 0
    ):
        return float(hour_avg) / float(daily_mean)
    return 1.0


def score_route(
    segments: list[RouteSegment], hour_profile: dict[str, Any] | None = None
) -> float:
    """Calculate the weighted raw exposure score for a list of route segments."""
    if not segments:
        return 0.0
    multiplier = _extract_hour_multiplier(hour_profile)
    total_travel_time = sum(seg.duration_min for seg in segments)
    if total_travel_time <= 0:
        return 0.0
    total_segment_scores = sum(
        score_segment(seg, multiplier) for seg in segments
    )
    return total_segment_scores / total_travel_time


def normalize_score(raw: float) -> tuple[int, str]:
    """Normalize raw exposure score to 0-100 range and assign label."""
    clamped = max(0.0, min(100.0, raw))
    score = round(clamped)
    if score <= 30:
        label = "Low"
    elif score <= 60:
        label = "Moderate"
    elif score <= 80:
        label = "High"
    else:
        label = "Very High"
    return score, label


def _generate_reason(best: RouteResult, baseline: RouteResult) -> str:
    """Generate comparative reason text between recommended route and baseline."""
    if best.route_id == baseline.route_id or baseline.exposure_score == 0:
        return (
            f"Route {best.route_id} has the lowest estimated exposure score of "
            f"{best.exposure_score} ({best.exposure_label})."
        )
    diff_pct = round(
        ((baseline.exposure_score - best.exposure_score) / baseline.exposure_score)
        * 100
    )
    time_diff = round(best.duration_min - baseline.duration_min)
    if time_diff > 0:
        return (
            f"Route {best.route_id} has ~{diff_pct}% lower estimated exposure "
            f"despite taking {time_diff} minutes longer."
        )
    if time_diff < 0:
        return (
            f"Route {best.route_id} has ~{diff_pct}% lower estimated exposure "
            f"and is {abs(time_diff)} minutes faster."
        )
    return (
        f"Route {best.route_id} has ~{diff_pct}% lower estimated exposure "
        f"with the same travel time."
    )


def compare_routes(routes: list[RouteResult]) -> dict[str, Any]:
    """Compare analyzed routes and return recommendation dictionary."""
    if not routes:
        return {
            "recommended_route": "",
            "reason": "No routes available for comparison.",
            "contributing_factors": [],
        }
    best_route = min(routes, key=lambda r: (r.exposure_score, r.duration_min))
    baseline = next(
        (r for r in routes if r.route_id != best_route.route_id), best_route
    )
    reason = _generate_reason(best_route, baseline)
    factors = best_route.contributing_factors or [
        {"factor": "traffic_density", "label": "Lower traffic along recommended route"},
        {"factor": "pm25", "label": f"Reduced PM2.5 along Route {best_route.route_id}"},
        {"factor": "travel_time", "label": "Optimized outdoor exposure window"},
    ]
    return {
        "recommended_route": best_route.route_id,
        "reason": reason,
        "contributing_factors": factors,
    }
