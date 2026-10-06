"""Data models for PATHwise pollution exposure and route analysis."""

from dataclasses import asdict, dataclass, field
from typing import Any


@dataclass
class RouteSegment:
    """Represents a discrete segment along a travel route."""

    lat: float
    lon: float
    aqi_class: str
    pm25: float
    duration_min: float
    congestion: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        """Convert segment to dictionary representation."""
        return asdict(self)


@dataclass
class RouteResult:
    """Represents scored exposure and metadata for an individual route."""

    route_id: str
    distance_km: float
    duration_min: float
    exposure_score: int
    exposure_label: str
    geometry: dict[str, Any]
    contributing_factors: list[dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        """Convert route result to dictionary representation."""
        return asdict(self)


@dataclass
class AnalysisResult:
    """Represents the complete response for a route exposure analysis."""

    routes: list[RouteResult]
    recommendation: dict[str, Any]
    time_profile: dict[str, Any]
    cached: bool = False

    def to_dict(self) -> dict[str, Any]:
        """Convert analysis result to dictionary representation."""
        return {
            "routes": [route.to_dict() for route in self.routes],
            "recommendation": self.recommendation,
            "time_profile": self.time_profile,
            "cached": self.cached,
        }
