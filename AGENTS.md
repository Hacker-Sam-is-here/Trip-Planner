# AGENTS.md — PATHwise (Pollution-Aware Trip Helper)

## What this project is

A web app that estimates a person's pollution exposure along a travel route
and recommends the lowest-exposure option. The user enters a start, destination,
travel mode, and departure time. The system returns 2-3 routes scored by
estimated pollution exposure with a plain-language explanation.

This is NOT a generic AQI dashboard. The core product is:
  environmental data + route + time → exposure score → recommendation → action

---

## Architecture

React (S3 + CloudFront)
↓
API Gateway (POST /analyze-route)
↓
Lambda (Python 3.12) — all business logic
├── Mapbox Directions API — route geometry, traffic, travel time
├── WAQI API — real-time AQ readings per station
├── OpenWeatherMap API — wind speed, wind direction, humidity, temp
├── OpenAQ historical API — hourly AQ averages for time-of-day scoring
└── air_quality_model.pkl — RandomForest classifier loaded from S3
↓
DynamoDB — cache results (1hr TTL), store demo scenarios
↓
S3 — model artifact, static assets

### Live Deployment Endpoints
- Frontend Web App: http://pathwise-web-808454010294.s3-website.ap-south-1.amazonaws.com
- CloudFront Distribution: Provisioning config in `infra/cloudfront_config.json` (awaiting AWS Support verification)
- API Gateway (HTTP API): https://9sy49ljh3a.execute-api.ap-south-1.amazonaws.com/analyze-route

---

## Folder structure

pathwise/
├── AGENTS.md
├── README.md
├── .env.example
├── backend/
│ ├── lambda_function.py — Lambda handler, entry point
│ ├── exposure_engine.py — core exposure calculation logic
│ ├── route_fetcher.py — Mapbox API integration
│ ├── aq_fetcher.py — WAQI + OpenAQ API integration
│ ├── weather_fetcher.py — OpenWeatherMap API integration
│ ├── time_profile.py — hourly AQ profile builder
│ ├── ml_classifier.py — loads model.pkl, runs inference
│ ├── dynamo_cache.py — DynamoDB read/write
│ ├── models.py — dataclasses / typed dicts for all data
│ └── requirements.txt
├── ml/
│ ├── air_quality_model.pkl — pre-trained RandomForestClassifier
│ ├── updated_pollution_dataset.csv
│ └── retrain.py — script to retrain if needed
├── frontend/
│ ├── src/
│ │ ├── App.jsx
│ │ ├── components/
│ │ │ ├── TripForm.jsx
│ │ │ ├── RouteMap.jsx
│ │ │ ├── ExposureCard.jsx
│ │ │ ├── RecommendationPanel.jsx
│ │ │ ├── FactorBars.jsx
│ │ │ └── TimeChart.jsx
│ │ ├── api/
│ │ │ └── analyzeRoute.js
│ │ └── utils/
│ │ └── scoring.js
│ ├── public/
│ └── package.json
├── infra/
│ ├── deploy.sh — S3 + Lambda deploy script
│ └── dynamo_setup.py — creates DynamoDB table
└── tests/
├── test_exposure_engine.py
├── test_ml_classifier.py
└── test_route_fetcher.py


---

## External APIs

### Mapbox Directions API
- Endpoint: `https://api.mapbox.com/directions/v5/mapbox/{profile}/{coords}`
- Profile: `mapbox/walking`, `mapbox/cycling`, `mapbox/driving-traffic`
- Params: `alternatives=true`, `geometries=geojson`, `steps=false`,
  `annotations=congestion_numeric,duration,distance`
- Returns: up to 3 route alternatives with geometry + per-segment congestion
- Env var: `MAPBOX_TOKEN`

### WAQI API (real-time AQ)
- Bounds endpoint: `https://api.waqi.info/map/bounds/?token={token}&latlng={bounds}`
- Feed detail endpoint: `https://api.waqi.info/feed/@{uid}/?token={token}`
- Returns: stations within a bounding box enriched with current AQI, PM2.5, PM10, NO2, SO2, CO
- Env var: `WAQI_TOKEN`

### OpenAQ API (historical hourly data - v3)
- Locations endpoint: `https://api.openaq.org/v3/locations` (params: coordinates, radius=25000, parameters_id=2)
- Measurements endpoint: `https://api.openaq.org/v3/locations/{id}/measurements` (params: parameters_id=2, limit=5000, date_from, date_to)
- Fallback: `DELHI_FALLBACK_PROFILE` (CPCB diurnal PM2.5 rush hour averages)
- Env var: `OPENAQ_API_KEY`

### OpenWeatherMap
- Endpoint: `https://api.openweathermap.org/data/2.5/weather?lat={}&lon={}`
- Returns: temp, humidity, wind_speed, wind_deg
- Env var: `OWM_API_KEY`

---

## ML model

File: `ml/air_quality_model.pkl`
Type: `sklearn.ensemble.RandomForestClassifier`
Input features (in this exact order):

Temperature, Humidity, PM2.5, PM10, NO2, SO2, CO,
Proximity_to_Industrial_Areas, Population_Density


Output: Air Quality label — one of {Good, Moderate, Poor, Hazardous}
(confirm exact labels by running `model.classes_` before integrating)

Load it once at Lambda cold start. Do not reload per request.

The model is used to estimate AQ at route segments where sensor coverage
is sparse. Given real sensor readings (PM2.5 etc.) + weather + location
characteristics, it outputs a quality class for that segment.

Feature importance is accessible via `model.feature_importances_`.
Surface the top 3 importances in the API response as `contributing_factors`.

---

## Exposure calculation

For each route, the system divides the polyline into segments.
For each segment:

segment_score = aqi_class_value(segment) × time_on_segment_minutes


AQ class → numeric value mapping:

Good → 25
Moderate → 50
Poor → 75
Hazardous → 100


Time-of-day multiplier (applied when hourly profile is available):

adjusted_score = segment_score × (hour_avg_pm25 / daily_mean_pm25)


Total route exposure:

raw_exposure = sum(segment_scores) / total_travel_time
normalized_exposure = min(100, raw_exposure)


Labels:

0–30 → Low
31–60 → Moderate
61–80 → High
81–100 → Very High


Present all scores as relative estimates. Never claim medical accuracy.

---

## API contract

### POST /analyze-route

Request:
```json
{
  "origin": "28.6139,77.2090",
  "destination": "28.5355,77.3910",
  "mode": "walking",
  "departure_time": "2026-10-08T08:00:00+05:30"
}
```

Response:
```json
{
  "routes": [
    {
      "route_id": "A",
      "distance_km": 8.2,
      "duration_min": 27,
      "exposure_score": 72,
      "exposure_label": "High",
      "geometry": { "type": "LineString", "coordinates": [...] }
    },
    {
      "route_id": "B",
      "distance_km": 9.1,
      "duration_min": 31,
      "exposure_score": 54,
      "exposure_label": "Moderate",
      "geometry": { "type": "LineString", "coordinates": [...] }
    }
  ],
  "recommendation": {
    "recommended_route": "B",
    "reason": "Route B has ~25% lower estimated exposure despite taking 4 minutes longer.",
    "contributing_factors": [
      { "factor": "traffic_density", "label": "Lower traffic near destination" },
      { "factor": "pm25", "label": "Reduced PM2.5 along Route B" },
      { "factor": "travel_time", "label": "Shorter outdoor exposure window" }
    ]
  },
  "time_profile": {
    "route": "B",
    "hours": [7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19],
    "scores": [78, 82, 68, 55, 48, 43, 46, 50, 55, 72, 80, 76, 61]
  },
  "cached": false
}
```

---

## AWS setup

### Lambda
- Runtime: Python 3.12
- Memory: 512 MB (needed for sklearn model in memory)
- Timeout: 15 seconds
- Layer or deployment package must include: pandas, scikit-learn, numpy,
  requests, boto3
- Environment variables: all API keys, S3 bucket name, DynamoDB table name
- Model loaded at module level (outside handler) so it persists across warm invocations

### DynamoDB
- Table: `pathwise-route-cache`
- Partition key: `cache_key` (string) — hash of origin+destination+mode+hour
- TTL attribute: `expires_at` (Unix timestamp, 1 hour ahead)
- On cache hit: return stored result directly, set `cached: true`

### S3
- Bucket: `pathwise-assets`
- Object key: `models/air_quality_model.pkl`
- Lambda downloads it on cold start if not already in `/tmp`

---

## Environment variables

MAPBOX_TOKEN=
WAQI_TOKEN=
OPENAQ_API_KEY=
OWM_API_KEY=
DYNAMO_TABLE=pathwise-route-cache
S3_BUCKET=pathwise-assets
S3_MODEL_KEY=models/air_quality_model.pkl
DEMO_CITY_LAT=28.6139
DEMO_CITY_LON=77.2090


---

## Coding rules

- Python backend: type hints on all functions, docstrings on public functions
- No function longer than 40 lines; split into helpers
- All external API calls wrapped in try/except with explicit fallback behavior
- Never raise an unhandled exception from the Lambda handler; always return
  a structured error response
- If an external API fails, fall back to cached DynamoDB data for that segment
- No hardcoded API keys anywhere; always read from environment variables
- Frontend: functional React components only, no class components
- No CSS frameworks except Tailwind utility classes
- Map library: Mapbox GL JS

---

## What not to build

- User accounts or authentication
- Real-time data streaming or websockets
- Health advice or medical interpretation of scores
- City-level AQI heatmap
- Public transit routing
- Mobile app
- Chat interface or LLM integration
- Any feature not directly serving: route comparison, exposure scoring,
  or recommendation explanation

---

## Testing expectations

Every module in `backend/` should have a corresponding test file.
Tests must cover:
- Normal case: valid inputs produce expected output shape
- Missing data: one API returns empty → graceful degradation, not crash
- Edge case: origin == destination
- Edge case: only one route returned by Mapbox

Run tests with `pytest tests/` before any Lambda deployment.

---

## Demo scenario (pre-loaded in DynamoDB)

Origin: Connaught Place, Delhi (28.6315, 77.2167)
Destination: Nehru Place, Delhi (28.5491, 77.2520)
Mode: driving
Time: 08:00 IST

This scenario returns 2 route alternatives (Route A: 68 High, Route B: 51 Moderate)
and must always work regardless of live API status. Pre-computed and stored in DynamoDB
with no TTL expiry (expires_at = 9999999999).