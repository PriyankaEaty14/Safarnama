export function stopCoordinates(stop) {
  const {lat, lng} = stop ?? {};
  return Number.isFinite(lat) && Math.abs(lat) <= 90 &&
    Number.isFinite(lng) && Math.abs(lng) <= 180 ? [lat, lng] : null;
}

export function googleMapsLinks(stop) {
  const coords = stopCoordinates(stop);
  if (!coords) return null;

  const point = coords.join(',');
  const search = new URL('https://www.google.com/maps/search/');
  search.search = new URLSearchParams({api: '1', query: point});
  const directions = new URL('https://www.google.com/maps/dir/');
  // Google Maps supplies the current location if available, or asks for a starting point.
  directions.search = new URLSearchParams({api: '1', destination: point, travelmode: 'walking'});
  return {search: search.href, directions: directions.href};
}

export function shapeCoordinates(geometry) {
  if (geometry?.status !== 'available' || !Array.isArray(geometry.coordinates)) return [];
  const points = geometry.coordinates.map(point => Array.isArray(point)
    ? stopCoordinates({lat: point[0], lng: point[1]})
    : null);
  return points.length >= 2 && points.every(Boolean) ? points : [];
}
