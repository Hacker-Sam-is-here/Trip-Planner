import React from "react";

export default function LoadingOverlay({ visible }) {
  if (!visible) return null;

  return (
    <div className="fixed inset-0 z-50 flex flex-col items-center justify-center bg-gray-900 bg-opacity-70 backdrop-blur-sm transition-opacity">
      <div className="relative">
        <div className="w-14 h-14 rounded-full border-4 border-gray-300 border-t-emerald-500 animate-spin"></div>
      </div>
      <p className="mt-4 text-white text-base font-medium tracking-wide">
        Analyzing your route...
      </p>
      <p className="mt-1 text-xs text-gray-300">
        Interpolating air quality & running exposure model
      </p>
    </div>
  );
}
