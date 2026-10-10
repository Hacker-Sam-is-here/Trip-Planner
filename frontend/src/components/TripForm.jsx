import React, { useState, useEffect } from "react";
import { MODES } from "../constants.js";
import { geocodePlace, isLatLon } from "../utils/geo.js";

export default function TripForm({ input, onChange, onSubmit, onDemoClick, loading }) {
  // Internal state for Origin
  const [originDisplay, setOriginDisplay] = useState(input.origin || "");
  const [originCoord, setOriginCoord] = useState(input.origin || null);
  const [originLabel, setOriginLabel] = useState(null);
  const [originGeocoding, setOriginGeocoding] = useState(false);
  const [originError, setOriginError] = useState(null);

  // Internal state for Destination
  const [destDisplay, setDestDisplay] = useState(input.destination || "");
  const [destCoord, setDestCoord] = useState(input.destination || null);
  const [destLabel, setDestLabel] = useState(null);
  const [destGeocoding, setDestGeocoding] = useState(false);
  const [destError, setDestError] = useState(null);

  // Synchronize when external input changes (e.g. Load Demo button or URL params)
  useEffect(() => {
    if (input.origin !== originDisplay && input.origin !== originCoord) {
      setOriginDisplay(input.origin || "");
      setOriginCoord(input.origin || null);
      setOriginLabel(null);
      setOriginGeocoding(false);
      setOriginError(null);
    }
  }, [input.origin]);

  useEffect(() => {
    if (input.destination !== destDisplay && input.destination !== destCoord) {
      setDestDisplay(input.destination || "");
      setDestCoord(input.destination || null);
      setDestLabel(null);
      setDestGeocoding(false);
      setDestError(null);
    }
  }, [input.destination]);

  // Origin field handlers
  const handleOriginChange = (e) => {
    const val = e.target.value;
    setOriginDisplay(val);
    setOriginError(null);
    if (!val.trim()) {
      setOriginCoord(null);
      setOriginLabel(null);
      setOriginGeocoding(false);
      onChange("origin", "");
    } else {
      setOriginCoord(null);
      setOriginLabel(null);
      onChange("origin", val);
    }
  };

  const handleOriginBlur = async () => {
    const query = originDisplay.trim();
    if (!query) {
      setOriginCoord(null);
      setOriginLabel(null);
      setOriginError(null);
      return;
    }

    setOriginGeocoding(true);
    setOriginError(null);
    try {
      const res = await geocodePlace(query);
      if (res) {
        const [lon, lat] = res;
        const coordStr = `${lat},${lon}`;
        setOriginCoord(coordStr);
        setOriginLabel(res.place_name || null);
        setOriginError(null);
        onChange("origin", coordStr);
      } else {
        setOriginCoord(null);
        setOriginLabel(null);
        if (!isLatLon(query)) {
          setOriginError("Place not found — try lat,lon format");
        }
      }
    } catch {
      setOriginCoord(null);
      setOriginLabel(null);
      if (!isLatLon(query)) {
        setOriginError("Place not found — try lat,lon format");
      }
    } finally {
      setOriginGeocoding(false);
    }
  };

  // Destination field handlers
  const handleDestChange = (e) => {
    const val = e.target.value;
    setDestDisplay(val);
    setDestError(null);
    if (!val.trim()) {
      setDestCoord(null);
      setDestLabel(null);
      setDestGeocoding(false);
      onChange("destination", "");
    } else {
      setDestCoord(null);
      setDestLabel(null);
      onChange("destination", val);
    }
  };

  const handleDestBlur = async () => {
    const query = destDisplay.trim();
    if (!query) {
      setDestCoord(null);
      setDestLabel(null);
      setDestError(null);
      return;
    }

    setDestGeocoding(true);
    setDestError(null);
    try {
      const res = await geocodePlace(query);
      if (res) {
        const [lon, lat] = res;
        const coordStr = `${lat},${lon}`;
        setDestCoord(coordStr);
        setDestLabel(res.place_name || null);
        setDestError(null);
        onChange("destination", coordStr);
      } else {
        setDestCoord(null);
        setDestLabel(null);
        if (!isLatLon(query)) {
          setDestError("Place not found — try lat,lon format");
        }
      }
    } catch {
      setDestCoord(null);
      setDestLabel(null);
      if (!isLatLon(query)) {
        setDestError("Place not found — try lat,lon format");
      }
    } finally {
      setDestGeocoding(false);
    }
  };

  const handleSubmit = (e) => {
    e.preventDefault();
    const finalOrigin = originCoord || originDisplay;
    const finalDest = destCoord || destDisplay;
    onChange("origin", finalOrigin);
    onChange("destination", finalDest);
    onSubmit();
  };

  return (
    <form onSubmit={handleSubmit} className="bg-white p-5 rounded-xl shadow-sm border border-gray-100">
      <div className="flex items-center justify-between mb-4">
        <h2 className="text-lg font-bold text-gray-800 tracking-tight">Plan Cleanest Route</h2>
        <button
          type="button"
          onClick={onDemoClick}
          disabled={loading}
          className="text-xs font-semibold px-3 py-1.5 rounded-md bg-indigo-50 text-indigo-700 hover:bg-indigo-100 border border-indigo-200 transition-colors disabled:opacity-50"
        >
          Load Demo
        </button>
      </div>

      <div className="space-y-3.5">
        <div>
          <label className="block text-xs font-semibold text-gray-600 uppercase tracking-wider mb-1">
            Origin
          </label>
          <div className="relative">
            <input
              type="text"
              value={originDisplay}
              onChange={handleOriginChange}
              onBlur={handleOriginBlur}
              placeholder="e.g. Karol Bagh or 28.6315,77.2167"
              required
              className="w-full px-3 py-2 pr-9 text-sm border border-gray-300 rounded-lg focus:ring-2 focus:ring-emerald-500 focus:border-emerald-500 outline-none transition-all placeholder-gray-400 font-mono"
            />
            {originGeocoding && (
              <div className="absolute right-3 top-1/2 -translate-y-1/2 pointer-events-none">
                <svg className="animate-spin h-4 w-4 text-emerald-600" viewBox="0 0 24 24" fill="none">
                  <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                  <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v8H4z"></path>
                </svg>
              </div>
            )}
          </div>
          {originLabel && !originGeocoding && (
            <div className="flex items-center text-xs text-emerald-700 mt-1.5 space-x-1">
              <svg className="w-3.5 h-3.5 text-emerald-600 flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2.5" d="M5 13l4 4L19 7" />
              </svg>
              <span className="truncate font-medium">📍 {originLabel}</span>
            </div>
          )}
          {originError && !originGeocoding && (
            <div className="flex items-center text-xs text-red-600 mt-1.5 space-x-1">
              <svg className="w-3.5 h-3.5 text-red-500 flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
              </svg>
              <span>{originError}</span>
            </div>
          )}
        </div>

        <div>
          <label className="block text-xs font-semibold text-gray-600 uppercase tracking-wider mb-1">
            Destination
          </label>
          <div className="relative">
            <input
              type="text"
              value={destDisplay}
              onChange={handleDestChange}
              onBlur={handleDestBlur}
              placeholder="e.g. Lajpat Nagar or 28.5491,77.2520"
              required
              className="w-full px-3 py-2 pr-9 text-sm border border-gray-300 rounded-lg focus:ring-2 focus:ring-emerald-500 focus:border-emerald-500 outline-none transition-all placeholder-gray-400 font-mono"
            />
            {destGeocoding && (
              <div className="absolute right-3 top-1/2 -translate-y-1/2 pointer-events-none">
                <svg className="animate-spin h-4 w-4 text-emerald-600" viewBox="0 0 24 24" fill="none">
                  <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                  <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v8H4z"></path>
                </svg>
              </div>
            )}
          </div>
          {destLabel && !destGeocoding && (
            <div className="flex items-center text-xs text-emerald-700 mt-1.5 space-x-1">
              <svg className="w-3.5 h-3.5 text-emerald-600 flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2.5" d="M5 13l4 4L19 7" />
              </svg>
              <span className="truncate font-medium">📍 {destLabel}</span>
            </div>
          )}
          {destError && !destGeocoding && (
            <div className="flex items-center text-xs text-red-600 mt-1.5 space-x-1">
              <svg className="w-3.5 h-3.5 text-red-500 flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
              </svg>
              <span>{destError}</span>
            </div>
          )}
        </div>

        <div className="grid grid-cols-2 gap-3">
          <div>
            <label className="block text-xs font-semibold text-gray-600 uppercase tracking-wider mb-1">
              Mode
            </label>
            <select
              value={input.mode}
              onChange={(e) => onChange("mode", e.target.value)}
              className="w-full px-3 py-2 text-sm border border-gray-300 rounded-lg focus:ring-2 focus:ring-emerald-500 focus:border-emerald-500 outline-none capitalize bg-white"
            >
              {MODES.map((mode) => (
                <option key={mode} value={mode}>
                  {mode}
                </option>
              ))}
            </select>
          </div>

          <div>
            <label className="block text-xs font-semibold text-gray-600 uppercase tracking-wider mb-1">
              Departure Time
            </label>
            <input
              type="datetime-local"
              value={input.departure_time ? input.departure_time.slice(0, 16) : ""}
              onChange={(e) => onChange("departure_time", e.target.value ? `${e.target.value}:00+05:30` : "")}
              required
              className="w-full px-3 py-2 text-sm border border-gray-300 rounded-lg focus:ring-2 focus:ring-emerald-500 focus:border-emerald-500 outline-none"
            />
          </div>
        </div>

        <button
          type="submit"
          disabled={loading}
          className="w-full mt-2 py-2.5 px-4 bg-emerald-600 hover:bg-emerald-700 text-white font-medium text-sm rounded-lg shadow-sm focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-emerald-500 disabled:opacity-60 transition-all flex items-center justify-center space-x-2"
        >
          {loading ? (
            <>
              <svg className="animate-spin h-4 w-4 text-white" viewBox="0 0 24 24" fill="none">
                <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v8H4z"></path>
              </svg>
              <span>Analyzing...</span>
            </>
          ) : (
            <span>Analyze Route</span>
          )}
        </button>

        <p className="text-xs text-gray-400 text-center pt-1">
          Scores are relative estimates, not medical measurements.
        </p>
      </div>
    </form>
  );
}

