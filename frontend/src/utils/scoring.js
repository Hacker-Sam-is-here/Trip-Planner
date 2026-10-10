import { EXPOSURE_COLORS, EXPOSURE_BG } from "../constants.js";

/**
 * Returns hex color from EXPOSURE_COLORS or fallback gray.
 * @param {string} label
 * @returns {string}
 */
export function getExposureColor(label) {
  return EXPOSURE_COLORS[label] || "#6b7280";
}

/**
 * Returns Tailwind class string from EXPOSURE_BG or fallback.
 * @param {string} label
 * @returns {string}
 */
export function getExposureBg(label) {
  return EXPOSURE_BG[label] || "bg-gray-100 text-gray-800";
}

/**
 * Formats duration in minutes into a human-readable string.
 * @param {number} minutes
 * @returns {string}
 */
export function formatDuration(minutes) {
  const rounded = Math.round(minutes);
  if (rounded < 60) {
    return `${rounded} min`;
  }
  const hours = Math.floor(rounded / 60);
  const remainingMins = rounded % 60;
  return `${hours}h ${remainingMins}m`;
}

/**
 * Formats distance in km.
 * @param {number} km
 * @returns {string}
 */
export function formatDistance(km) {
  return `${Number(km).toFixed(1)} km`;
}

/**
 * Calculates exposure reduction percentage rounded to nearest 5%.
 * Returns null if absolute score difference is less than 5.
 * @param {number} scoreA
 * @param {number} scoreB
 * @returns {string | null}
 */
export function getReductionPercent(scoreA, scoreB) {
  if (typeof scoreA !== "number" || typeof scoreB !== "number") {
    return null;
  }
  const diff = Math.abs(scoreA - scoreB);
  if (diff < 5) {
    return null;
  }
  const higher = Math.max(scoreA, scoreB);
  const lower = Math.min(scoreA, scoreB);
  if (higher <= 0) {
    return null;
  }
  const pct = Math.round((((higher - lower) / higher) * 100) / 5) * 5;
  if (pct <= 0) {
    return null;
  }
  return `~${pct}% lower`;
}
