from pathlib import Path
from unittest.mock import MagicMock, patch
import pytest
import requests
from backend.aq_fetcher import (
    estimate_aq_at_point,
    get_station_detail,
    get_stations_in_bounds,
)
from backend.ml_classifier import load_model
from backend.models import RouteSegment
from backend.route_fetcher import get_routes
from backend.segment_scorer import score_route_segments
from backend.time_profile import DELHI_FALLBACK_PROFILE, build_hourly_profile
from backend.weather_fetcher import get_weather

MODEL_PATH = Path(__file__).resolve().parent.parent / "ml" / "air_quality_model.pkl"


def test_get_weather_fallback_on_exception(monkeypatch: pytest.MonkeyPatch) -> None:
    """get_weather returns fallback dict when requests.get raises."""
    monkeypatch.setenv("OWM_API_KEY", "test_key")
    with patch("requests.get", side_effect=requests.RequestException("Network failed")):
        result = get_weather(28.61, 77.20)
        assert result == {
            "temperature": 25.0,
            "humidity": 60.0,
            "wind_speed": 2.0,
            "wind_deg": 0.0,
        }


def test_get_stations_in_bounds_non_200(monkeypatch: pytest.MonkeyPatch) -> None:
    """get_stations_in_bounds returns [] on non-200 response."""
    monkeypatch.setenv("WAQI_TOKEN", "test_token")
    mock_resp = MagicMock()
    mock_resp.status_code = 500
    with patch("requests.get", return_value=mock_resp):
        stations = get_stations_in_bounds(28.5, 77.1, 28.7, 77.3)
        assert stations == []


def test_get_station_detail_http_failure(monkeypatch: pytest.MonkeyPatch) -> None:
    """get_station_detail returns all -1.0 on HTTP failure."""
    monkeypatch.setenv("WAQI_TOKEN", "test_token")
    with patch("requests.get", side_effect=requests.RequestException("Feed error")):
        res = get_station_detail(2554)
        assert res == {"pm25": -1.0, "pm10": -1.0, "no2": -1.0, "so2": -1.0, "co": -1.0}


def test_get_station_detail_parses_feed(monkeypatch: pytest.MonkeyPatch) -> None:
    """get_station_detail correctly parses a mocked WAQI feed response."""
    monkeypatch.setenv("WAQI_TOKEN", "test_token")
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {
        "status": "ok",
        "data": {
            "iaqi": {
                "pm25": {"v": 112.5},
                "pm10": {"v": 140.0},
                "no2": {"v": 22.1},
                "so2": {"v": 9.4},
                "co": {"v": 2.1},
            }
        },
    }
    with patch("requests.get", return_value=mock_resp):
        res = get_station_detail(2554)
        assert res["pm25"] == 112.5
        assert res["pm10"] == 140.0
        assert res["no2"] == 22.1
        assert res["so2"] == 9.4
        assert res["co"] == 2.1


def test_get_stations_in_bounds_merges_detail(monkeypatch: pytest.MonkeyPatch) -> None:
    """get_stations_in_bounds merges detail data into station dicts."""
    monkeypatch.setenv("WAQI_TOKEN", "test_token")

    def mock_get(url: str, *args, **kwargs) -> MagicMock:
        resp = MagicMock()
        resp.status_code = 200
        if "map/bounds" in url:
            resp.json.return_value = {
                "status": "ok",
                "data": [{"lat": 28.6, "lon": 77.2, "uid": 1234, "aqi": 90}],
            }
        elif "feed/@1234" in url:
            resp.json.return_value = {
                "status": "ok",
                "data": {"iaqi": {"pm25": {"v": 45.0}, "pm10": {"v": 85.0}}},
            }
        return resp

    with patch("requests.get", side_effect=mock_get):
        stations = get_stations_in_bounds(28.5, 77.1, 28.7, 77.3)
        assert len(stations) == 1
        assert stations[0]["uid"] == 1234
        assert stations[0]["pm25"] == 45.0
        assert stations[0]["pm10"] == 85.0


def test_estimate_aq_at_point_empty_stations_fallback() -> None:
    """estimate_aq_at_point returns conservative fallback when stations=[]."""
    result = estimate_aq_at_point(28.6, 77.2, [])
    assert result == {
        "aqi": 100,
        "pm25": 50.0,
        "pm10": 80.0,
        "no2": 30.0,
        "so2": 10.0,
        "co": 1.5,
    }


def test_estimate_aq_at_point_weights_closer_station() -> None:
    """estimate_aq_at_point correctly weights closer station more heavily."""
    target_lat, target_lon = 28.0, 77.0
    st_near = {
        "lat": 28.05,
        "lon": 77.0,
        "aqi": 30,
        "pm25": 20.0,
        "pm10": 40.0,
        "no2": 15.0,
        "so2": 5.0,
        "co": 0.5,
    }
    st_far = {
        "lat": 28.40,
        "lon": 77.0,
        "aqi": 180,
        "pm25": 140.0,
        "pm10": 160.0,
        "no2": 60.0,
        "so2": 25.0,
        "co": 3.0,
    }

    result = estimate_aq_at_point(target_lat, target_lon, [st_near, st_far])
    midpoint_pm25 = (st_near["pm25"] + st_far["pm25"]) / 2.0
    assert result["pm25"] < midpoint_pm25
    assert result["aqi"] < (st_near["aqi"] + st_far["aqi"]) / 2.0


def test_get_routes_assigns_ids_in_order(monkeypatch: pytest.MonkeyPatch) -> None:
    """get_routes assigns route_ids A, B, C in order."""
    monkeypatch.setenv("MAPBOX_TOKEN", "test_token")
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {
        "routes": [
            {
                "distance": 5000,
                "duration": 900,
                "geometry": {
                    "type": "LineString",
                    "coordinates": [[77.2, 28.6], [77.21, 28.61]],
                },
            },
            {
                "distance": 5500,
                "duration": 1000,
                "geometry": {
                    "type": "LineString",
                    "coordinates": [[77.2, 28.6], [77.22, 28.62]],
                },
            },
            {
                "distance": 6000,
                "duration": 1100,
                "geometry": {
                    "type": "LineString",
                    "coordinates": [[77.2, 28.6], [77.23, 28.63]],
                },
            },
        ]
    }

    with patch("requests.get", return_value=mock_resp):
        routes = get_routes("28.6,77.2", "28.65,77.25", "walking")
        assert len(routes) == 3
        assert routes[0]["route_id"] == "A"
        assert routes[1]["route_id"] == "B"
        assert routes[2]["route_id"] == "C"


def test_get_routes_returns_empty_on_failure(monkeypatch: pytest.MonkeyPatch) -> None:
    """get_routes returns [] on request failure."""
    monkeypatch.setenv("MAPBOX_TOKEN", "test_token")
    with patch("requests.get", side_effect=requests.RequestException("API error")):
        routes = get_routes("28.6,77.2", "28.65,77.25", "walking")
        assert routes == []


def test_build_hourly_profile_empty_locations_fallback(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """build_hourly_profile returns DELHI_FALLBACK_PROFILE when locations call returns empty."""
    monkeypatch.setenv("OPENAQ_API_KEY", "test_key")
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {"results": []}

    with patch("requests.get", return_value=mock_resp):
        profile = build_hourly_profile(28.6, 77.2)
        assert profile == DELHI_FALLBACK_PROFILE


def test_build_hourly_profile_measurements_error_fallback(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """build_hourly_profile returns DELHI_FALLBACK_PROFILE when measurements call returns error."""
    monkeypatch.setenv("OPENAQ_API_KEY", "test_key")

    def mock_get(url: str, *args, **kwargs) -> MagicMock:
        resp = MagicMock()
        if "locations" in url and "measurements" not in url:
            resp.status_code = 200
            resp.json.return_value = {
                "results": [{"id": 101, "distance": 1200.0}]
            }
        else:
            resp.status_code = 500
        return resp

    with patch("requests.get", side_effect=mock_get):
        profile = build_hourly_profile(28.6, 77.2)
        assert profile == DELHI_FALLBACK_PROFILE


def test_build_hourly_profile_groups_readings_by_hour(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """build_hourly_profile correctly groups mocked readings by hour."""
    monkeypatch.setenv("OPENAQ_API_KEY", "test_key")

    def mock_get(url: str, *args, **kwargs) -> MagicMock:
        resp = MagicMock()
        resp.status_code = 200
        if "locations" in url and "measurements" not in url:
            resp.json.return_value = {
                "results": [{"id": 101, "distance": 1200.0}]
            }
        else:
            resp.json.return_value = {
                "results": [
                    {"datetime_utc": "2026-10-01T07:15:00Z", "value": 100.0},
                    {"datetime_utc": "2026-10-01T07:45:00Z", "value": 120.0},
                    {"datetime_utc": "2026-10-01T08:15:00Z", "value": 150.0},
                    {"datetime_utc": "2026-10-01T09:15:00Z", "value": 130.0},
                ]
            }
        return resp

    with patch("requests.get", side_effect=mock_get):
        profile = build_hourly_profile(28.6, 77.2)
        assert profile[7] == 110.0
        assert profile[8] == 150.0
        assert profile[9] == 130.0


def test_score_route_segments_produces_one_per_segment() -> None:
    """score_route_segments produces one RouteSegment per segment in route."""
    model = load_model(str(MODEL_PATH))
    mock_route = {
        "route_id": "A",
        "distance_km": 5.0,
        "duration_min": 25.0,
        "segments": [
            {"lat": 28.61, "lon": 77.20, "duration_min": 8.0, "congestion": 0.2},
            {"lat": 28.62, "lon": 77.21, "duration_min": 9.0, "congestion": 0.6},
            {"lat": 28.63, "lon": 77.22, "duration_min": 8.0, "congestion": 0.4},
        ],
    }
    stations = [
        {
            "lat": 28.615,
            "lon": 77.205,
            "aqi": 60,
            "pm25": 40.0,
            "pm10": 70.0,
            "no2": 25.0,
            "so2": 8.0,
            "co": 1.0,
        }
    ]
    weather = {
        "temperature": 28.0,
        "humidity": 55.0,
        "wind_speed": 3.0,
        "wind_deg": 120.0,
    }
    hour_profile = {h: 50.0 for h in range(24)}

    scored = score_route_segments(
        route=mock_route,
        stations=stations,
        weather=weather,
        hour_profile=hour_profile,
        model=model,
        departure_hour=8,
    )
    assert len(scored) == 3
    for seg in scored:
        assert isinstance(seg, RouteSegment)
        assert seg.aqi_class in {"Good", "Moderate", "Poor", "Hazardous"}
        assert seg.duration_min > 0
