import React, { useRef, useState } from "react";
import { getExposureColor } from "../utils/scoring.js";

function getAqiLabel(score) {
  if (score <= 30) return "Low";
  if (score <= 60) return "Moderate";
  if (score <= 80) return "High";
  return "Very High";
}

export default function TimeChart({ time_profile }) {
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

  // Adaptive label step to prevent crowding (C3)
  const step = count > 14 ? 3 : count > 7 ? 2 : 1;

  const handleTouch = (data) => {
    setHovered(data);
    if (touchTimerRef.current) {
      clearTimeout(touchTimerRef.current);
    }
    touchTimerRef.current = setTimeout(() => {
      setHovered(null);
    }, 2000);
  };

  return (
    <div className="bg-white p-4 rounded-xl border border-gray-100 shadow-sm">
      <div className="flex items-center justify-between mb-1">
        <h4 className="text-sm font-bold text-gray-800">
          Best time to travel — Route {route}
        </h4>
        {hovered !== null ? (
          <span className="text-xs font-semibold text-gray-700 bg-gray-100 px-2 py-0.5 rounded">
            {hovered.hour}:00 — {hovered.label} ({hovered.score})
          </span>
        ) : (
          <span className="text-xs text-gray-400">Hover or tap for details</span>
        )}
      </div>
      <p className="text-xs text-gray-400 mb-2">Lower is better</p>

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

            const data = { index: idx, hour, score, label };

            return (
              <g
                key={`${hour}-${idx}`}
                onMouseEnter={() => setHovered(data)}
                onMouseLeave={() => setHovered(null)}
                onTouchStart={() => handleTouch(data)}
                onClick={() => handleTouch(data)}
                className="cursor-pointer"
              >
                <rect
                  x={x}
                  y={y}
                  width={barWidth}
                  height={barH}
                  rx="3"
                  fill={color}
                  opacity={isHovered ? 1 : 0.85}
                  className="transition-all duration-150"
                />

                {/* Show spaced hour labels */}
                {idx % step === 0 && (
                  <text
                    x={x + barWidth / 2}
                    y={chartHeight + 22}
                    textAnchor="middle"
                    className="text-[10px] fill-gray-400 select-none font-mono"
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
