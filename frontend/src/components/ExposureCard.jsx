import React from "react";
import {
  formatDistance,
  formatDuration,
  getExposureBg,
  getExposureColor,
  getReductionPercent,
} from "../utils/scoring.js";

export default function ExposureCard({
  route,
  isSelected,
  isRecommended,
  onSelect,
  highestScore,
}) {
  const reduction =
    isRecommended && highestScore && highestScore > route.exposure_score
      ? getReductionPercent(highestScore, route.exposure_score)
      : null;

  const borderColor = isSelected
    ? getExposureColor(route.exposure_label)
    : "#e5e7eb";

  return (
    <div
      onClick={() => onSelect(route.route_id)}
      style={{ borderColor, borderWidth: "2px" }}
      className={`p-4 rounded-xl cursor-pointer transition-all bg-white shadow-sm hover:shadow-md ${
        isSelected ? "ring-2 ring-offset-1 ring-emerald-500" : ""
      }`}
    >
      <div className="flex items-center justify-between mb-2">
        <div className="flex items-center space-x-2">
          <span className="font-bold text-gray-900 text-base">
            Route {route.route_id}
          </span>
          {isRecommended && (
            <span className="bg-emerald-100 text-emerald-800 text-xs px-2 py-0.5 rounded-full font-semibold border border-emerald-300">
              Recommended
            </span>
          )}
        </div>
        <span
          className={`text-xs px-2.5 py-1 rounded-full font-semibold ${getExposureBg(
            route.exposure_label
          )}`}
        >
          {route.exposure_label}
        </span>
      </div>

      <div className="flex items-baseline justify-between mt-3">
        <div>
          <span className="text-2xl font-extrabold text-gray-900">
            {route.exposure_score}
          </span>
          <span className="text-xs text-gray-500 font-medium">/100 exposure</span>
        </div>
        <div className="text-right text-xs text-gray-600 space-x-2">
          <span>{formatDistance(route.distance_km)}</span>
          <span>•</span>
          <span className="font-medium">
            {formatDuration(route.duration_min)}
          </span>
        </div>
      </div>

      {reduction !== null && (
        <div className="mt-2.5 pt-2 border-t border-gray-100 text-xs text-emerald-700 font-medium flex items-center">
          <svg
            className="w-3.5 h-3.5 mr-1 text-emerald-600"
            fill="none"
            viewBox="0 0 24 24"
            stroke="currentColor"
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth="2"
              d="M13 17h8m0 0V9m0 8l-8-8-4 4-6-6"
            />
          </svg>
          <span>{reduction} exposure</span>
        </div>
      )}
    </div>
  );
}
