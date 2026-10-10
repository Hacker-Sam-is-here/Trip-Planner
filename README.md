# PATHwise

> Instead of telling people how polluted their city is, we tell them
> how much pollution they are likely to be exposed to — and what they
> can do to reduce it.

## The problem

City-level AQI gives everyone the same number regardless of where
they travel, which route they take, or how long they are outside.
A person commuting through a high-traffic corridor has meaningfully
higher exposure than someone taking a quieter route, even in the
same city on the same day.

## Our solution

PATHwise combines real-time air quality readings, weather conditions,
traffic data, and route geometry to estimate a personalized pollution
exposure score for each route option. It then recommends the
lower-exposure choice and explains why.

## Key features

- Route comparison with per-route exposure scores (Low / Moderate /
  High / Very High)
- Plain-language explanation of contributing factors
- Time-of-day chart showing best departure windows
- Graceful fallback to cached results if any live API is unavailable

## Architecture

```
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
```

## AWS services

| Service | Role |
|---|---|
| Lambda (Python 3.12) | All business logic, exposure calculation, ML inference |
| API Gateway (HTTP API) | Exposes POST /analyze-route to the frontend |
| DynamoDB | Route result cache with 1hr TTL; permanent demo scenario |
| S3 | ML model artifact storage; static frontend hosting |
| CloudFront | HTTPS CDN for the React frontend |
| CloudWatch | Lambda logs and error monitoring |

## AI/ML methodology

The system uses a pre-trained RandomForestClassifier to assign an
air quality class (Good / Moderate / Poor / Hazardous) to each
route segment based on:

  Temperature, Humidity, PM2.5, PM10, NO2, SO2, CO,
  Proximity to industrial areas (approximated from traffic congestion),
  Population density (location-based static value)

Exposure for each segment is:
  segment_score = class_value × time_on_segment_minutes

Total route exposure is the time-weighted mean of all segment scores,
normalized to 0–100. Scores are relative estimates, not medical
measurements.

The time-of-day chart uses historical PM2.5 readings from OpenAQ v3
to model diurnal pollution patterns at the origin area. For locations
without sufficient historical data, a validated fallback profile based
on published CPCB Delhi seasonal averages is used.

## Data sources

| Source | Data | License |
|---|---|---|
| WAQI | Real-time AQI + pollutant readings | Non-commercial use |
| OpenAQ v3 | Historical PM2.5 hourly data | CC BY 4.0 |
| OpenWeatherMap | Temperature, humidity, wind | Free tier |
| Mapbox Directions API | Route geometry, traffic | Commercial (free tier) |
| Kaggle — Air Quality and Pollution Assessment (Mujtaba Mateen) | RF classifier training data | Apache 2.0 |

## Results

For the Delhi demo scenario (Connaught Place → Nehru Place, driving, 8am):
- Route A: 13.44 km, 40.2 min — exposure score 68 (High)
- Route B: 13.95 km, 41.5 min — exposure score 51 (Moderate)
- Route B provides approximately 25% lower estimated exposure
  despite taking ~1.3 minutes longer

All scores are model-based relative estimates.

## Environmental impact

The system helps users identify lower-exposure routes and departure
times. In the demo scenario, choosing Route B over Route A produces
a ~25% reduction in estimated exposure score. At scale across a
city's commuters, consistent route optimization could meaningfully
reduce population-level pollution exposure without requiring any
change in infrastructure.

## Screenshots

- **Initial State**: Clean dual-panel layout with origin/destination inputs, mode selector, and Mapbox dark vector tiles.
- **Route Comparison Result**: Recommended Route B banner, comparative exposure cards (Route A 68 High vs. Route B 51 Moderate), key contributing factor bars, and diurnal travel time SVG chart.
- **Mobile Responsive View**: Compact vertical layout with fixed-height route map on top and scrollable trip details below.

## How to run locally

```bash
cd backend
pip install -r requirements.txt
# Add API keys to .env
RUN_INTEGRATION=1 pytest tests/test_integration_local.py

cd frontend
npm install
npm run dev
```

## Deployment

```bash
bash infra/deploy.sh
```

Requires AWS CLI configured with appropriate permissions.
See infra/deploy.sh for full provisioning steps.

## Live demo

- Production Web App: http://pathwise-web-808454010294.s3-website.ap-south-1.amazonaws.com
- CloudFront (Pending Account Verification): See `infra/cloudfront_config.json` and `infra/deploy_cloudfront.sh`
- API Gateway Endpoint: https://9sy49ljh3a.execute-api.ap-south-1.amazonaws.com/analyze-route

## Demo video

[YouTube link here]

## Team

Sam

## AI tools used

- Claude (Anthropic) — architecture design, code generation, prompt engineering for development phases
- GitHub Copilot — code completion and test generation

All generated code was reviewed, tested, and verified by the team.
