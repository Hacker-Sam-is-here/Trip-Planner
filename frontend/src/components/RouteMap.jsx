import React, { useEffect, useRef, useState } from "react";
import mapboxgl from "mapbox-gl";
import { EXPOSURE_COLORS } from "../constants.js";
import { getBounds } from "../utils/geo.js";
import { getExposureColor } from "../utils/scoring.js";

function getRouteGeometryHash(route) {
  const coords = route?.geometry?.coordinates || [];
  const sample = coords.slice(0, 5).concat(coords.slice(-5));
  return JSON.stringify(sample);
}

export default function RouteMap({
  routes,
  selectedRoute,
  onRouteSelect,
  recommendation,
  cached,
}) {
  const mapContainerRef = useRef(null);
  const mapRef = useRef(null);
  const [mapLoaded, setMapLoaded] = useState(false);
  const activeLayersRef = useRef([]);

  // Initialize Mapbox map on mount
  useEffect(() => {
    mapboxgl.accessToken = import.meta.env.VITE_MAPBOX_TOKEN || "";

    const map = new mapboxgl.Map({
      container: mapContainerRef.current,
      style: "mapbox://styles/mapbox/dark-v11",
      center: [77.2167, 28.6315], // Default Delhi center
      zoom: 11,
    });

    map.on("load", () => {
      setMapLoaded(true);
    });

    mapRef.current = map;

    return () => {
      map.remove();
    };
  }, []);

  // Update sources and layers when routes change
  useEffect(() => {
    const map = mapRef.current;
    if (!map || !mapLoaded) return;

    // 1. Remove previous layers and sources
    activeLayersRef.current.forEach(({ sourceId, layerId }) => {
      if (map.getLayer(layerId)) {
        map.removeLayer(layerId);
      }
      if (map.getSource(sourceId)) {
        map.removeSource(sourceId);
      }
    });
    activeLayersRef.current = [];

    if (!routes || routes.length === 0) return;

    // Deduplicate routes by geometry hash (C1)
    const seenGeometries = new Set();
    const uniqueRoutes = routes.filter((route) => {
      const hash = getRouteGeometryHash(route);
      if (seenGeometries.has(hash)) return false;
      seenGeometries.add(hash);
      return true;
    });

    // 2. Add each route
    uniqueRoutes.forEach((route) => {
      const sourceId = `route-${route.route_id}`;
      const layerId = `layer-${route.route_id}`;

      map.addSource(sourceId, {
        type: "geojson",
        data: route.geometry,
      });

      const isSelected = selectedRoute === route.route_id;

      map.addLayer({
        id: layerId,
        type: "line",
        source: sourceId,
        layout: {
          "line-join": "round",
          "line-cap": "round",
        },
        paint: {
          "line-color": getExposureColor(route.exposure_label),
          "line-width": isSelected ? 7 : 4,
          "line-opacity": 0.9,
        },
      });

      // Click handler
      map.on("click", layerId, () => {
        if (onRouteSelect) onRouteSelect(route.route_id);
      });

      map.on("mouseenter", layerId, () => {
        map.getCanvas().style.cursor = "pointer";
      });

      map.on("mouseleave", layerId, () => {
        map.getCanvas().style.cursor = "";
      });

      activeLayersRef.current.push({
        sourceId,
        layerId,
        routeId: route.route_id,
      });
    });

    // 3. Fit bounds
    const bounds = getBounds(routes);
    map.fitBounds(bounds, {
      padding: 60,
      maxZoom: 15,
      duration: 1000,
    });
  }, [routes, mapLoaded]);

  // Update line width when selectedRoute changes without re-adding sources
  useEffect(() => {
    const map = mapRef.current;
    if (!map || !mapLoaded) return;

    activeLayersRef.current.forEach(({ layerId, routeId }) => {
      if (map.getLayer(layerId)) {
        const isSelected = routeId === selectedRoute;
        map.setPaintProperty(layerId, "line-width", isSelected ? 7 : 4);
      }
    });
  }, [selectedRoute, mapLoaded]);

  const hasRoutes = routes && routes.length > 0;

  return (
    <div className="relative w-full h-full min-h-[300px]">
      <div ref={mapContainerRef} className="w-full h-full" />

      {/* Live / Cached badge in top-right (B3) */}
      {hasRoutes && typeof cached === "boolean" && (
        <div className="absolute top-4 right-4 z-10 bg-gray-900/85 backdrop-blur-xs px-3 py-1 rounded-full border border-gray-700/60 text-white text-xs shadow-md flex items-center space-x-1.5">
          <span
            className={`w-2 h-2 rounded-full ${
              cached ? "bg-amber-400" : "bg-emerald-400 animate-pulse"
            }`}
          />
          <span className="text-gray-200 text-xs font-medium">
            {cached ? "Cached result" : "Live data"}
          </span>
        </div>
      )}

      {/* Empty state overlay */}
      {!hasRoutes && (
        <div className="absolute inset-0 flex items-center justify-center pointer-events-none z-10">
          <div className="bg-gray-900/80 backdrop-blur-xs text-gray-200 text-sm font-medium px-4 py-2.5 rounded-full border border-gray-700/60 shadow-lg">
            Enter a trip to see routes
          </div>
        </div>
      )}

      {/* Legend in bottom-left */}
      <div className="absolute bottom-4 left-4 z-10 bg-gray-900/85 backdrop-blur-xs px-3.5 py-2.5 rounded-lg border border-gray-700/60 text-white text-xs shadow-md">
        <p className="font-semibold text-gray-300 text-[11px] uppercase tracking-wider mb-1.5">
          Exposure Level
        </p>
        <div className="grid grid-cols-2 gap-x-3 gap-y-1">
          {Object.entries(EXPOSURE_COLORS).map(([label, color]) => (
            <div key={label} className="flex items-center space-x-1.5">
              <span
                className="w-2.5 h-2.5 rounded-full flex-shrink-0"
                style={{ backgroundColor: color }}
              />
              <span className="text-gray-200 text-xs">{label}</span>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
