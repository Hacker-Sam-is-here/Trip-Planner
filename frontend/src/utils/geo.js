/**
 * Returns [lon, lat] of the midpoint coordinate of a LineString geometry.
 * @param {{ coordinates: number[][] }} geometry
 * @returns {[number, number]}
 */
export function getMidpoint(geometry) {
  if (!geometry || !geometry.coordinates || geometry.coordinates.length === 0) {
    return [77.2090, 28.6139];
  }
  const coords = geometry.coordinates;
  const midIndex = Math.floor(coords.length / 2);
  return coords[midIndex];
}

/**
 * Computes bounding box across all route geometries combined.
 * @param {Array<{ geometry: { coordinates: number[][] } }>} routes
 * @returns {[[number, number], [number, number]]}
 */
export function getBounds(routes) {
  if (!routes || routes.length === 0) {
    return [
      [77.1000, 28.5000],
      [77.3000, 28.7000],
    ];
  }
  let minLon = Infinity;
  let minLat = Infinity;
  let maxLon = -Infinity;
  let maxLat = -Infinity;

  for (const route of routes) {
    const coords = route.geometry?.coordinates || [];
    for (const [lon, lat] of coords) {
      if (lon < minLon) minLon = lon;
      if (lat < minLat) minLat = lat;
      if (lon > maxLon) maxLon = lon;
      if (lat > maxLat) maxLat = lat;
    }
  }

  if (minLon === Infinity) {
    return [
      [77.1000, 28.5000],
      [77.3000, 28.7000],
    ];
  }

  return [
    [minLon, minLat],
    [maxLon, maxLat],
  ];
}

/**
 * Checks if a string is in lat,lon format (two comma-separated numbers).
 * @param {string} query
 * @returns {boolean}
 */
export function isLatLon(query) {
  if (!query || typeof query !== "string") return false;
  return /^\s*[+-]?\d+(?:\.\d+)?\s*,\s*[+-]?\d+(?:\.\d+)?\s*$/.test(query.trim());
}

/**
 * Geocodes a place name or address to [lon, lat] using Mapbox Geocoding API.
 * If query matches lat,lon format, parses and returns [lon, lat] directly without API call.
 * @param {string} query
 * @returns {Promise<[number, number] | null>}
 */
export async function geocodePlace(query) {
  if (!query || typeof query !== "string") {
    return null;
  }
  const trimmed = query.trim();
  if (!trimmed) {
    return null;
  }

  // If query already matches lat,lon format, parse and return [lon, lat] directly
  const latLonMatch = trimmed.match(/^\s*([+-]?\d+(?:\.\d+)?)\s*,\s*([+-]?\d+(?:\.\d+)?)\s*$/);
  if (latLonMatch) {
    const lat = parseFloat(latLonMatch[1]);
    const lon = parseFloat(latLonMatch[2]);
    if (!isNaN(lat) && !isNaN(lon)) {
      return [lon, lat];
    }
  }

  const token = import.meta.env.VITE_MAPBOX_TOKEN;
  if (!token) {
    return null;
  }

  const encoded = encodeURIComponent(trimmed);
  const url = `https://api.mapbox.com/geocoding/v5/mapbox.places/${encoded}.json?access_token=${token}&country=in&limit=1&proximity=77.2090,28.6139`;

  try {
    const response = await fetch(url);
    if (!response.ok) {
      return null;
    }
    const data = await response.json();
    if (data && Array.isArray(data.features) && data.features.length > 0) {
      const feature = data.features[0];
      if (Array.isArray(feature.center) && feature.center.length >= 2) {
        const coords = [feature.center[0], feature.center[1]];
        coords.place_name = feature.place_name;
        return coords;
      }
    }
    return null;
  } catch (err) {
    return null;
  }
}
