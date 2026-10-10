import React, { useRef, useState } from "react";
import { getExposureColor } from "../utils/scoring.js";

function getAqiLabel(score) {
  if (score <= 30) return "Low";
  if (score <= 60) return "Moderate";
  if (score <= 80) return "High";
  return "Very High";
}

export default function TimeChart({ time_profile, onSelectHour }) {
  const [hovered, setHovered] = useState(null);
  const touchTimerRef = useRef(null);

  if (
    !time_profile ||
    !time_profile.hours ||
    !time_profile.scores ||
    time_profile.hours.length === 0
  ) {
    return null;
  }

  const { route, hours, scores } = time_profile;
  const chartHeight = 55;
  const totalWidth = 360;
  const paddingX = 12;
  const availableWidth = totalWidth - paddingX * 2;
  const count = Math.max(1, hours.length);
  const slotWidth = availableWidth / count;
  const barWidth = Math.max(4, Math.min(24, slotWidth * 0.68));

  // Determine scale max (handle scores clamped or unclamped)
  const maxScore = Math.max(100, ...scores);

  // Find cleanest hour
  const minScore = Math.min(...scores);
  const bestIdx = scores.indexOf(minScore);
  const bestHour = hours[bestIdx];

  // Adaptive label step to prevent crowding (C3)
  const step = count > 14 ? 3 : count > 7 ? 2 : 1;

  const handleTouch = (data) => {
    setHovered(data);
    if (touchTimerRef.current) {
      clearTimeout(touchTimerRef.current);
    }
    touchTimerRef.current = setTimeout(() => {
      setHovered(null);
    }, 3000);
  };

  const handleBarClick = (data) => {
    if (onSelectHour) {
      onSelectHour(data.hour);
    }
  };

  return (
    <div className="bg-white p-4 rounded-xl border border-gray-100 shadow-sm">
      <div className="flex items-center justify-between mb-2">
        <h4 className="text-sm font-bold text-gray-800">
          Best time to travel — Route {route}
        </h4>
        {onSelectHour && (
          <button
            type="button"
            onClick={() => onSelectHour(bestHour)}
            className="text-[11px] font-semibold text-emerald-700 bg-emerald-50 hover:bg-emerald-100 border border-emerald-300 px-2 py-0.5 rounded-md transition-colors flex items-center space-x-1"
            title={`Click to shift departure to ${bestHour}:00 for lowest exposure`}
          >
            <span>✨ Best at {bestHour}:00</span>
            <span className="text-[9px] bg-emerald-600 text-white px-1 py-0.2 rounded font-bold">Shift</span>
          </button>
        )}
      </div>

      <div className="flex items-center justify-between mb-2">
        {hovered !== null ? (
          <div className="flex items-center space-x-2">
            <span className="text-xs font-semibold text-gray-700 bg-gray-100 px-2 py-0.5 rounded">
              {hovered.hour}:00 — {hovered.label} ({hovered.score}/100)
            </span>
            {onSelectHour && (
              <button
                type="button"
                onClick={() => onSelectHour(hovered.hour)}
                className="text-[11px] font-bold text-white bg-emerald-600 hover:bg-emerald-700 px-2 py-0.5 rounded transition-all shadow-xs"
              >
                Depart at {hovered.hour}:00 →
              </button>
            )}
          </div>
        ) : (
          <span className="text-xs text-gray-400">Click any hour to test departure</span>
        )}
        <span className="text-[11px] text-gray-400">Lower is better</span>
      </div>

      <div className="w-full">
        <svg
          viewBox={`0 0 ${totalWidth} 85`}
          className="w-full h-[100px] overflow-visible"
        >
          {/* Baseline grid */}
          <line
            x1={paddingX}
            y1={chartHeight + 8}
            x2={totalWidth - paddingX}
            y2={chartHeight + 8}
            stroke="#e5e7eb"
            strokeWidth="1"
          />

          {hours.map((hour, idx) => {
            const score = scores[idx] ?? 0;
            const label = getAqiLabel(score);
            const color = getExposureColor(label);
            const barH = Math.max(
              4,
              Math.min(chartHeight, (score / maxScore) * chartHeight)
            );
            const x = paddingX + idx * slotWidth + (slotWidth - barWidth) / 2;
            const y = chartHeight + 8 - barH;

            const isHovered = hovered && hovered.index === idx;
            const isBest = hour === bestHour;

            const data = { index: idx, hour, score, label };

            return (
              <g
                key={`${hour}-${idx}`}
                onMouseEnter={() => setHovered(data)}
                onMouseLeave={() => setHovered(null)}
                onTouchStart={() => handleTouch(data)}
                onClick={() => handleBarClick(data)}
                className="cursor-pointer"
              >
                <rect
                  x={x}
                  y={y}
                  width={barWidth}
                  height={barH}
                  rx="3"
                  fill={color}
                  stroke={isBest ? "#059669" : "none"}
                  strokeWidth={isBest ? 1.5 : 0}
                  opacity={isHovered ? 1 : 0.85}
                  className="transition-all duration-150 hover:brightness-110"
                />

                {/* Show spaced hour labels */}
                {idx % step === 0 && (
                  <text
                    x={x + barWidth / 2}
                    y={chartHeight + 22}
                    textAnchor="middle"
                    className={`text-[10px] select-none font-mono ${
                      isBest ? "fill-emerald-600 font-bold" : "fill-gray-400"
                    }`}
                  >
                    {hour}h
                  </text>
                )}
              </g>
            );
          })}
        </svg>
      </div>
    </div>
  );
}
