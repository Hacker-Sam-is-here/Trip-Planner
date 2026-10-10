"""Fetch real Mapbox directions for the demo scenario and save raw JSON."""

import json
import os
from pathlib import Path
import sys
from dotenv import load_dotenv
import requests

ROOT_DIR = Path(__file__).resolve().parent.parent
load_dotenv(ROOT_DIR / ".env")


def fetch_mapbox_demo_routes() -> dict:
    """Call Mapbox Directions API for Karol Bagh to Lajpat Nagar."""
    token = os.getenv("MAPBOX_TOKEN", "").strip()
    if not token:
        print("Error: MAPBOX_TOKEN not found in environment.")
        sys.exit(1)

    coords = "77.1907,28.6514;77.2373,28.5700"
    url = f"https://api.mapbox.com/directions/v5/mapbox/driving-traffic/{coords}"
    params = {
        "access_token": token,
        "alternatives": "true",
        "geometries": "geojson",
        "overview": "full",
        "annotations": "congestion_numeric,duration,distance",
    }
    resp = requests.get(url, params=params, timeout=12)
    resp.raise_for_status()
    return resp.json()


def process_and_save_routes(data: dict) -> None:
    """Validate, print summary, and save raw response to file."""
    routes = data.get("routes", [])
    if len(routes) < 2:
        print(f"Warning: Mapbox returned only {len(routes)} route(s). Expected at least 2.")
        sys.exit(1)

    for i, route in enumerate(routes[:2]):
        coords = route.get("geometry", {}).get("coordinates", [])
        route_label = "Route A" if i == 0 else "Route B"
        first_coord = coords[0] if coords else None
        last_coord = coords[-1] if coords else None
        print(f"{route_label}: {len(coords)} coordinate points")
        print(f"  First coordinate: {first_coord}")
        print(f"  Last coordinate:  {last_coord}")

    out_path = ROOT_DIR / "infra" / "demo_routes_raw.json"
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)
    print(f"Saved full raw response to {out_path}")


def main() -> None:
    """Entry point to fetch and reseed demo routes."""
    print("Fetching demo routes from Mapbox Directions API...")
    data = fetch_mapbox_demo_routes()
    process_and_save_routes(data)


if __name__ == "__main__":
    main()
