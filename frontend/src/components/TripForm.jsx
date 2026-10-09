import React from "react";
import { MODES } from "../constants.js";

export default function TripForm({ input, onChange, onSubmit, onDemoClick, loading }) {
  const handleSubmit = (e) => {
    e.preventDefault();
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
          <input
            type="text"
            value={input.origin}
            onChange={(e) => onChange("origin", e.target.value)}
            placeholder="28.6315,77.2167 or address"
            required
            className="w-full px-3 py-2 text-sm border border-gray-300 rounded-lg focus:ring-2 focus:ring-emerald-500 focus:border-emerald-500 outline-none transition-all placeholder-gray-400 font-mono"
          />
        </div>

        <div>
          <label className="block text-xs font-semibold text-gray-600 uppercase tracking-wider mb-1">
            Destination
          </label>
          <input
            type="text"
            value={input.destination}
            onChange={(e) => onChange("destination", e.target.value)}
            placeholder="28.5491,77.2520 or address"
            required
            className="w-full px-3 py-2 text-sm border border-gray-300 rounded-lg focus:ring-2 focus:ring-emerald-500 focus:border-emerald-500 outline-none transition-all placeholder-gray-400 font-mono"
          />
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
