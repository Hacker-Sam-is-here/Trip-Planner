import React from "react";
import { getReductionPercent } from "../utils/scoring.js";

export default function RecommendationPanel({ recommendation, routes }) {
  if (!recommendation) return null;

  let reductionText = null;
  if (routes && routes.length >= 2) {
    const recommendedRoute = routes.find(
      (r) => r.route_id === recommendation.recommended_route
    );
    const otherScores = routes
      .filter((r) => r.route_id !== recommendation.recommended_route)
      .map((r) => r.exposure_score);
    if (recommendedRoute && otherScores.length > 0) {
      const maxOther = Math.max(...otherScores);
      reductionText = getReductionPercent(
        maxOther,
        recommendedRoute.exposure_score
      );
    }
  }

  const isSingleRoute = !routes || routes.length <= 1;
  const reasonText = isSingleRoute
    ? "Only one route available."
    : recommendation.reason;

  return (
    <div className="bg-green-50 border border-green-200 p-4 rounded-xl shadow-xs">
      <div className="flex items-center space-x-2">
        <div className="p-1 bg-green-500 rounded-md text-white">
          <svg
            className="w-4 h-4"
            fill="none"
            viewBox="0 0 24 24"
            stroke="currentColor"
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth="2.5"
              d="M5 13l4 4L19 7"
            />
          </svg>
        </div>
        <h3 className="text-base font-bold text-green-900">
          Recommended: Route {recommendation.recommended_route}
        </h3>
      </div>
      <p className="mt-2 text-sm text-green-800 leading-relaxed">
        {reasonText}
      </p>
      {!isSingleRoute && reductionText !== null && (
        <div className="mt-2.5 inline-block bg-white text-green-700 text-xs px-2.5 py-1 rounded-md font-semibold border border-green-200">
          Estimated {reductionText} exposure
        </div>
      )}
    </div>
  );
}
