export function journeySegments(journey, details = []) {
  const enriched = new Map(details.map(segment => [segment.from + '|' + segment.to, segment]));
  return journey.legs.flatMap((leg, legIndex) => leg.stopIds.slice(0, -1).map((from, index) => {
    const to = leg.stopIds[index + 1];
    const supplied = leg.segments?.find(segment => segment.from === from && segment.to === to);
    return {...supplied, ...enriched.get(from + '|' + to), from, to, route: leg.route, legIndex, index};
  }));
}

export function compareJourneys(journeys) {
  const earliest = [...journeys].sort((a, b) => a.arrival - b.arrival)[0];
  return {earliest};
}

export function laterQuery(query, offset) {
  const instant = new Date(query.date + 'T' + query.time + ':00Z');
  instant.setUTCMinutes(instant.getUTCMinutes() + offset);
  const iso = instant.toISOString();
  return {...query, date: iso.slice(0, 10), time: iso.slice(11, 16)};
}

export function scheduledStops(leg) {
  return leg.stopIds.map((id, index) => {
    const supplied = leg.stopTimes?.[index];
    const first = index === 0;
    const last = index === leg.stopIds.length - 1;
    return {
      id, first, last,
      arrival: supplied?.arrival ?? (last ? leg.end : null),
      departure: supplied?.departure ?? (first ? leg.start : null),
    };
  });
}

function toPaise(value) {
  return Number.isFinite(value) && value >= 0 ? Math.round(value * 100) : null;
}

export function journeyFare(journey) {
  const total = toPaise(journey.fareInr);
  if (total !== null) return total / 100;
  const fares = journey.legs.map(leg => toPaise(leg.fareInr));
  return fares.length && fares.every(fare => fare !== null)
    ? fares.reduce((sum, fare) => sum + fare, 0) / 100
    : null;
}

export function transferBetween(previous, next) {
  const from = previous.stopIds.at(-1);
  const to = next.stopIds[0];
  const arrival = scheduledStops(previous).at(-1)?.arrival;
  const departure = scheduledStops(next)[0]?.departure;
  return {
    from, to, arrival, departure,
    minutes: Number.isFinite(arrival) && Number.isFinite(departure) && departure >= arrival ? departure - arrival : null,
  };
}

export function callsAtStop(journey, stopId, serviceDate, now) {
  const serviceStart = Date.parse(serviceDate + 'T00:00:00+05:30');
  const minute = Math.floor((now - serviceStart) / 60000);
  return journey.legs.flatMap((leg, legIndex) => scheduledStops(leg).flatMap((stop, index) => {
    if (stop.id !== stopId) return [];
    const arrival = stop.arrival;
    const departure = stop.departure;
    const firstTime = arrival ?? departure;
    const lastTime = departure ?? arrival;
    let state = 'unknown';
    if (Number.isFinite(minute) && Number.isFinite(firstTime) && Number.isFinite(lastTime)) {
      if (minute < firstTime) state = 'upcoming';
      else if (minute <= lastTime) state = 'due';
      else state = departure == null ? 'arrival-passed' : 'departed';
    }
    return [{route:leg.route, legIndex, index, state, arrival, departure}];
  }));
}
