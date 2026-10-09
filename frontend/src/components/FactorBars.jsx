import React from "react";

const FIXED_WIDTHS = ["90%", "65%", "45%", "30%"];

const FACTOR_ICONS = {
  traffic_density: "🚗",
  pm25: "💨",
  travel_time: "⏱️",
  weather: "🌬️",
};

function getFactorIcon(factorKey) {
  return FACTOR_ICONS[factorKey] || "⚠️";
}

export default function FactorBars({ factors }) {
  if (!factors || factors.length === 0) return null;

  return (
    <div className="bg-white p-4 rounded-xl border border-gray-100 shadow-sm">
      <h4 className="text-xs font-bold text-gray-500 uppercase tracking-wider mb-3">
        Key Contributing Factors
      </h4>
      <div className="space-y-3">
        {factors.map((item, idx) => {
          const width = FIXED_WIDTHS[idx] || "25%";
          const icon = getFactorIcon(item.factor);
          return (
            <div key={item.factor || idx}>
              <div className="flex justify-between text-xs text-gray-700 font-medium mb-1 items-center">
                <span className="flex items-center space-x-1.5">
                  <span className="text-sm">{icon}</span>
                  <span>{item.label}</span>
                </span>
              </div>
              <div className="w-full bg-gray-100 h-2 rounded-full overflow-hidden">
                <div
                  className="bg-orange-400 h-full rounded-full transition-all duration-500"
                  style={{ width }}
                ></div>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
