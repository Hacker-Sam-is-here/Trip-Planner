import React, { useEffect, useRef, useState } from "react";
import mapboxgl from "mapbox-gl";
import { EXPOSURE_COLORS } from "../constants.js";
import { getBounds } from "../utils/geo.js";
import { getExposureColor } from "../utils/scoring.js";

function getRouteGeometryHash(route) {
  const coords = route?.geometry?.coordinates || [];
  return JSON.stringify(coords);
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
  const markersRef = useRef([]);
  const popupRef = useRef(null);

  // Initialize Mapbox map on mount
  useEffect(() => {
    mapboxgl.accessToken = import.meta.env.VITE_MAPBOX_TOKEN || "";

    const map = new mapboxgl.Map({
      container: mapContainerRef.current,
      style: "mapbox://styles/mapbox/dark-v11",
      center: [77.2167, 28.6315], // Default Delhi center
      zoom: 11,
    });

    popupRef.current = new mapboxgl.Popup({
      closeButton: false,
      closeOnClick: false,
      offset: 12,
    });

    map.on("load", () => {
      setMapLoaded(true);
    });

    mapRef.current = map;

    return () => {
      markersRef.current.forEach((m) => m.remove());
      if (popupRef.current) popupRef.current.remove();
      map.remove();
    };
  }, []);

  // Update sources, layers, and markers when routes change
  useEffect(() => {
    const map = mapRef.current;
    if (!map || !mapLoaded) return;

    // 1. Remove previous layers, sources, and markers
    activeLayersRef.current.forEach(({ sourceId, layerId }) => {
      if (map.getLayer(layerId)) {
        map.removeLayer(layerId);
      }
      if (map.getSource(sourceId)) {
        map.removeSource(sourceId);
      }
    });
    activeLayersRef.current = [];

    markersRef.current.forEach((m) => m.remove());
    markersRef.current = [];

    if (!routes || routes.length === 0) return;

    // Deduplicate routes by full geometry hash (C1)
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
          "line-opacity": isSelected ? 0.95 : 0.6,
        },
      });

      // Click handler to select route
      map.on("click", layerId, () => {
        if (onRouteSelect) onRouteSelect(route.route_id);
      });

      // Hover handler to display route details popup
      map.on("mousemove", layerId, (e) => {
        map.getCanvas().style.cursor = "pointer";
        const color = getExposureColor(route.exposure_label);
        const html = `
          <div class="px-2.5 py-1.5 text-xs text-white bg-gray-900/95 rounded-lg shadow-lg border border-gray-700/80 font-sans pointer-events-none">
            <div class="flex items-center space-x-1.5 mb-1">
              <span class="w-2.5 h-2.5 rounded-full flex-shrink-0" style="background-color: ${color}"></span>
              <span class="font-bold text-sm text-gray-100">Route ${route.route_id}</span>
              <span class="text-[11px] px-1.5 py-0.5 rounded font-medium bg-gray-800 text-gray-300">${route.exposure_label}</span>
            </div>
            <div class="text-gray-300 font-medium">Exposure Score: <span class="font-bold text-white">${route.exposure_score}</span>/100</div>
            <div class="text-gray-400 text-[11px] mt-0.5">${route.distance_km} km • ${Math.round(route.duration_min)} min</div>
          </div>
        `;
        if (popupRef.current) {
          popupRef.current
            .setLngLat(e.lngLat)
            .setHTML(html)
            .addTo(map);
        }
      });

      map.on("mouseleave", layerId, () => {
        map.getCanvas().style.cursor = "";
        if (popupRef.current) popupRef.current.remove();
      });

      activeLayersRef.current.push({
        sourceId,
        layerId,
        routeId: route.route_id,
      });
    });

    // 3. Add Custom Start and Finish Markers
    const firstRouteCoords = routes[0]?.geometry?.coordinates || [];
    if (firstRouteCoords.length >= 2) {
      const startCoord = firstRouteCoords[0];
      const endCoord = firstRouteCoords[firstRouteCoords.length - 1];

      // Start Marker
      const startEl = document.createElement("div");
      startEl.className = "flex flex-col items-center cursor-pointer pointer-events-auto group";
      startEl.innerHTML = `
        <div class="relative flex items-center justify-center">
          <div class="absolute w-8 h-8 bg-emerald-500 rounded-full animate-ping opacity-35"></div>
          <div class="relative w-8 h-8 bg-emerald-600 border-2 border-white rounded-full shadow-lg flex items-center justify-center text-white">
            <span class="font-black text-xs">A</span>
          </div>
        </div>
        <div class="mt-1 bg-gray-900/95 text-[11px] font-bold text-emerald-400 px-2 py-0.5 rounded shadow border border-gray-700/60 whitespace-nowrap">
          Start
        </div>
      `;

      // Destination Marker
      const destEl = document.createElement("div");
      destEl.className = "flex flex-col items-center cursor-pointer pointer-events-auto group";
      destEl.innerHTML = `
        <div class="relative flex items-center justify-center">
          <div class="absolute w-8 h-8 bg-rose-500 rounded-full animate-ping opacity-35"></div>
          <div class="relative w-8 h-8 bg-rose-600 border-2 border-white rounded-full shadow-lg flex items-center justify-center text-white">
            <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2.5" d="M3 21v-4m0 0V5a2 2 0 012-2h6.5l1 1H21l-3 6 3 6h-8.5l-1-1H5a2 2 0 00-2 2zm9-13.5V9"/>
            </svg>
          </div>
        </div>
        <div class="mt-1 bg-gray-900/95 text-[11px] font-bold text-rose-400 px-2 py-0.5 rounded shadow border border-gray-700/60 whitespace-nowrap">
          Finish
        </div>
      `;

      const startMarker = new mapboxgl.Marker({ element: startEl, anchor: "top" })
        .setLngLat(startCoord)
        .addTo(map);

      const destMarker = new mapboxgl.Marker({ element: destEl, anchor: "top" })
        .setLngLat(endCoord)
        .addTo(map);

      markersRef.current.push(startMarker, destMarker);
    }

    // Bring selected route to top
    if (selectedRoute) {
      const selectedLayer = `layer-${selectedRoute}`;
      if (map.getLayer(selectedLayer)) {
        map.moveLayer(selectedLayer);
      }
    }

    // 4. Fit bounds
    const bounds = getBounds(routes);
    map.fitBounds(bounds, {
      padding: 70,
      maxZoom: 15,
      duration: 1000,
    });
  }, [routes, mapLoaded]);

  // Update line width and opacity when selectedRoute changes without re-adding sources
  useEffect(() => {
    const map = mapRef.current;
    if (!map || !mapLoaded) return;

    activeLayersRef.current.forEach(({ layerId, routeId }) => {
      if (map.getLayer(layerId)) {
        const isSelected = routeId === selectedRoute;
        map.setPaintProperty(layerId, "line-width", isSelected ? 7 : 4);
        map.setPaintProperty(layerId, "line-opacity", isSelected ? 0.95 : 0.6);
        if (isSelected) {
          map.moveLayer(layerId);
        }
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
