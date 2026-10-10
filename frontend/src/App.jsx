import React, { useEffect, useState } from "react";
import { DEMO_INPUT, DEMO_RESULT } from "./constants.js";
import { analyzeRoute } from "./api/analyzeRoute.js";
import TripForm from "./components/TripForm.jsx";
import RouteMap from "./components/RouteMap.jsx";
import ExposureCard from "./components/ExposureCard.jsx";
import RecommendationPanel from "./components/RecommendationPanel.jsx";
import FactorBars from "./components/FactorBars.jsx";
import TimeChart from "./components/TimeChart.jsx";
import LoadingOverlay from "./components/LoadingOverlay.jsx";
import ErrorBanner from "./components/ErrorBanner.jsx";

export default function App() {
  const [input, setInput] = useState(() => {
    if (typeof window !== "undefined") {
      const view = new URLSearchParams(window.location.search).get("view");
      if (view === "demo" || view === "routeA") {
        return DEMO_INPUT;
      }
    }
    const now = new Date();
    const pad = (n) => String(n).padStart(2, "0");
    const defaultTime = `${now.getFullYear()}-${pad(now.getMonth() + 1)}-${pad(now.getDate())}T${pad(now.getHours())}:00:00+05:30`;
    return {
      origin: "",
      destination: "",
      mode: "driving",
      departure_time: defaultTime,
    };
  });

  const [result, setResult] = useState(() => {
    if (typeof window !== "undefined") {
      const view = new URLSearchParams(window.location.search).get("view");
      if (view === "demo" || view === "routeA") {
        return DEMO_RESULT;
      }
    }
    return null;
  });

  const [loading, setLoading] = useState(
    () =>
      typeof window !== "undefined" &&
      new URLSearchParams(window.location.search).get("view") === "loading"
  );
  const [progress, setProgress] = useState(0);
  const [progressVisible, setProgressVisible] = useState(false);
  const [error, setError] = useState(null);
  const [selectedRoute, setSelectedRoute] = useState(() => {
    if (typeof window !== "undefined") {
      const view = new URLSearchParams(window.location.search).get("view");
      if (view === "routeA") return "A";
      if (view === "demo") return "B";
    }
    return null;
  });
  const [isConfigMissing, setIsConfigMissing] = useState(false);

  useEffect(() => {
    const apiUrl = import.meta.env.VITE_API_URL;
    if (!apiUrl) {
      setError("VITE_API_URL is not configured. Add it to .env and restart.");
      setIsConfigMissing(true);
      return;
    }

    if (typeof window !== "undefined") {
      const params = new URLSearchParams(window.location.search);
      const view = params.get("view");
      if (view === "loading") {
        setLoading(true);
      } else if (view === "demo") {
        setInput(DEMO_INPUT);
      } else if (view === "routeA") {
        setInput(DEMO_INPUT);
      }
    }
  }, []);

  const handleInputChange = (field, value) => {
    setInput((prev) => ({ ...prev, [field]: value }));
  };

  const executeAnalysis = async (params) => {
    setLoading(true);
    setError(null);
    setResult(null);
    setSelectedRoute(null);
    setProgressVisible(true);
    setProgress(15);
    const pTimer = setTimeout(() => setProgress(85), 150);

    try {
      const data = await analyzeRoute(params);
      setResult(data);
      if (data?.recommendation?.recommended_route) {
        setSelectedRoute(data.recommendation.recommended_route);
      }
    } catch (err) {
      setError(err.message || "Failed to analyze route.");
    } finally {
      clearTimeout(pTimer);
      setProgress(100);
      setTimeout(() => {
        setProgressVisible(false);
        setProgress(0);
      }, 400);
      setLoading(false);
    }
  };

  const handleSubmit = () => {
    executeAnalysis(input);
  };

  const handleDemoClick = () => {
    setInput(DEMO_INPUT);
    executeAnalysis(DEMO_INPUT);
  };

  const handleHourSelect = (hour) => {
    const dateStr = input.departure_time
      ? input.departure_time.slice(0, 10)
      : new Date().toISOString().slice(0, 10);
    const newDepartureTime = `${dateStr}T${String(hour).padStart(2, "0")}:00:00+05:30`;
    const updatedInput = { ...input, departure_time: newDepartureTime };
    setInput(updatedInput);
    executeAnalysis(updatedInput);
  };

  // If VITE_API_URL is missing, show only ErrorBanner
  if (isConfigMissing) {
    return (
      <div className="min-h-screen bg-gray-50 p-6 flex flex-col items-center justify-center">
        <div className="w-full max-w-lg">
          <ErrorBanner message={error} onDismiss={null} />
        </div>
      </div>
    );
  }

  const highestScore =
    result?.routes?.length > 0
      ? Math.max(...result.routes.map((r) => r.exposure_score))
      : 0;

  return (
    <div className="h-screen w-screen flex flex-col md:flex-row overflow-hidden bg-gray-100">
      {/* Top progress bar (B5) */}
      {progressVisible && (
        <div className="fixed top-0 left-0 right-0 h-1 z-[100] bg-transparent pointer-events-none">
          <div
            className="h-full bg-emerald-500 shadow-sm"
            style={{
              width: `${progress}%`,
              opacity: progress === 100 ? 0 : 1,
              transition:
                progress === 100
                  ? "width 150ms ease-out, opacity 250ms 150ms ease-out"
                  : "width 500ms ease-out",
            }}
          />
        </div>
      )}

      <LoadingOverlay visible={loading} />

      {/* Left Panel: 40% width on desktop, full scrollable */}
      <div className="w-full md:w-[40%] h-auto md:h-full overflow-y-auto flex flex-col p-4 md:p-6 space-y-4 bg-gray-50 border-r border-gray-200 order-2 md:order-1">
        <div className="flex items-center space-x-2 pb-2 border-b border-gray-200">
          <div className="w-7 h-7 rounded-lg bg-emerald-600 flex items-center justify-center text-white font-black text-sm">
            P
          </div>
          <div>
            <h1 className="text-lg font-extrabold text-gray-900 tracking-tight">
              PATHwise
            </h1>
            <p className="text-xs text-gray-500">
              Pollution-Aware Trip Exposure Helper
            </p>
          </div>
        </div>

        <ErrorBanner message={error} onDismiss={() => setError(null)} />

        <TripForm
          input={input}
          onChange={handleInputChange}
          onSubmit={handleSubmit}
          onDemoClick={handleDemoClick}
          loading={loading}
        />

        {/* Loading skeleton placeholder cards (B1) */}
        {loading && !result && (
          <div className="space-y-3 pt-1">
            <div className="h-4 w-32 bg-gray-200 rounded animate-pulse"></div>
            <div className="bg-white p-4 rounded-xl border border-gray-100 shadow-sm animate-pulse space-y-3">
              <div className="flex justify-between items-center">
                <div className="h-5 w-24 bg-gray-200 rounded"></div>
                <div className="h-5 w-16 bg-gray-200 rounded-full"></div>
              </div>
              <div className="flex justify-between items-baseline pt-1">
                <div className="h-8 w-20 bg-gray-200 rounded"></div>
                <div className="h-4 w-28 bg-gray-200 rounded"></div>
              </div>
            </div>
            <div className="bg-white p-4 rounded-xl border border-gray-100 shadow-sm animate-pulse space-y-3">
              <div className="flex justify-between items-center">
                <div className="h-5 w-24 bg-gray-200 rounded"></div>
                <div className="h-5 w-16 bg-gray-200 rounded-full"></div>
              </div>
              <div className="flex justify-between items-baseline pt-1">
                <div className="h-8 w-20 bg-gray-200 rounded"></div>
                <div className="h-4 w-28 bg-gray-200 rounded"></div>
              </div>
            </div>
          </div>
        )}

        {result && (
          <div className="space-y-4 pt-1">
            <RecommendationPanel
              recommendation={result.recommendation}
              routes={result.routes}
            />

            <div className="space-y-2.5">
              <h3 className="text-xs font-bold text-gray-500 uppercase tracking-wider">
                Route Comparison
              </h3>
              {result.routes?.map((route) => (
                <ExposureCard
                  key={route.route_id}
                  route={route}
                  isSelected={selectedRoute === route.route_id}
                  isRecommended={
                    route.route_id === result.recommendation?.recommended_route
                  }
                  onSelect={(id) => setSelectedRoute(id)}
                  highestScore={highestScore}
                />
              ))}
            </div>

            <FactorBars
              factors={result.recommendation?.contributing_factors}
            />

            <TimeChart
              time_profile={result.time_profile}
              onSelectHour={handleHourSelect}
            />
          </div>
        )}
      </div>

      {/* Right Panel: 60% width on desktop, fixed height/map */}
      <div className="w-full md:w-[60%] h-[300px] md:h-full order-1 md:order-2 bg-gray-900">
        <RouteMap
          routes={result?.routes || []}
          selectedRoute={selectedRoute}
          onRouteSelect={(id) => setSelectedRoute(id)}
          recommendation={result?.recommendation}
          cached={result?.cached}
        />
      </div>
    </div>
  );
}
