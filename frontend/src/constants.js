export const EXPOSURE_COLORS = {
  Low: "#22c55e",       // green-500
  Moderate: "#eab308",  // yellow-500
  High: "#f97316",      // orange-500
  "Very High": "#ef4444" // red-500
};

export const EXPOSURE_BG = {
  Low: "bg-green-100 text-green-800",
  Moderate: "bg-yellow-100 text-yellow-800",
  High: "bg-orange-100 text-orange-800",
  "Very High": "bg-red-100 text-red-800"
};

export const MODES = ["walking", "cycling", "driving"];

export const DEMO_INPUT = {
  origin: "28.6315,77.2167",
  destination: "28.5491,77.2520",
  mode: "driving",
  departure_time: "2026-10-09T08:00:00+05:30"
};

export const DEMO_RESULT = {
  routes: [
    {
      route_id: "A",
      distance_km: 13.44,
      duration_min: 40.2,
      exposure_score: 68,
      exposure_label: "High",
      geometry: {
        type: "LineString",
        coordinates: [
          [77.2167, 28.6315],
          [77.225, 28.61],
          [77.235, 28.58],
          [77.252, 28.5491]
        ]
      },
      contributing_factors: []
    },
    {
      route_id: "B",
      distance_km: 13.95,
      duration_min: 41.5,
      exposure_score: 51,
      exposure_label: "Moderate",
      geometry: {
        type: "LineString",
        coordinates: [
          [77.2167, 28.6315],
          [77.23, 28.62],
          [77.24, 28.58],
          [77.252, 28.5491]
        ]
      },
      contributing_factors: []
    }
  ],
  recommendation: {
    recommended_route: "B",
    reason: "Route B has ~25% lower estimated exposure despite taking 1 minute longer.",
    contributing_factors: [
      {
        factor: "traffic_density",
        label: "Lower traffic near destination"
      },
      {
        factor: "pm25",
        label: "Reduced PM2.5 along Route B"
      },
      {
        factor: "travel_time",
        label: "Shorter outdoor exposure window"
      }
    ]
  },
  time_profile: {
    route: "B",
    hours: [7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19],
    scores: [82, 85, 78, 65, 52, 45, 42, 46, 55, 68, 76, 80, 72]
  },
  cached: true
};
