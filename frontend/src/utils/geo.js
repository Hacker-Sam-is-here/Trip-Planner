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
