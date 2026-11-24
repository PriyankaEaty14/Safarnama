"""Resolve crowding requests against ordered GTFS stops and service calendars."""

from datetime import date
import json

from sqlalchemy import text

from app.adapters.ml_adapter import SegmentKey
from app.services.journey_service import active_services, MAX_GTFS_HOUR, SEARCH_WINDOW


class SegmentContextError(ValueError):
    def __init__(self, message, status=422):
        super().__init__(message)
        self.status = status


def _date_offset(day, offset):
    ordinal = day.toordinal() + offset
    return date.fromordinal(ordinal) if 1 <= ordinal <= date.max.toordinal() else None


def _direction(code, direction):
    if direction is not None:
        return direction
    code = (code or "").strip().upper()
    return next((suffix for suffix in ("DOWN", "UP") if code.endswith(suffix)), None)


def segment_from_query(db, route_id, direction, start, end, day, minute):
    route = db.execute(text("SELECT short_name FROM routes WHERE id=:route"), {"route": route_id}).first()
    if route is None:
        raise SegmentContextError("GTFS route not found", 404)
    stops = db.execute(text("SELECT id FROM stops WHERE id IN (:start, :end)"),
                       {"start": start, "end": end}).scalars().all()
    if start == end:
        raise SegmentContextError("Boarding and alighting stops must differ")
    if len(stops) != 2:
        raise SegmentContextError("GTFS stop not found", 404)
    active = active_services(db, day)
    candidates = db.execute(text("""
        SELECT DISTINCT t.service_id, t.direction_id FROM trips t
        JOIN stop_times boarding ON t.id=boarding.trip_id
        JOIN stop_times alighting ON t.id=alighting.trip_id
        WHERE t.route_id=:route AND boarding.stop_id=:start AND alighting.stop_id=:end
          AND boarding.stop_sequence<alighting.stop_sequence
          AND boarding.departure IS NOT NULL AND alighting.arrival>=boarding.departure
    """), {"route": route_id, "start": start, "end": end}).all()
    directions = {
        _direction(route.short_name, item.direction_id)
        for item in candidates
        if item.service_id in active and (
            direction is None or direction in {item.direction_id, _direction(route.short_name, None)}
        )
    }
    if not directions:
        raise SegmentContextError("No active ordered GTFS segment matches this request")
    resolved = next(iter(directions)) if len(directions) == 1 else None
    return SegmentKey(route_id, direction or resolved, start, end, day, minute)


def segments_from_journey(db, journey_id, day, requested_minute):
    try:
        legs = json.loads(journey_id)
    except (ValueError, RecursionError) as error:
        raise SegmentContextError("Invalid journey ID") from error
    if not isinstance(legs, list) or not 1 <= len(legs) <= 2:
        raise SegmentContextError("Invalid journey ID")
    keys = []
    previous_arrival = None
    for leg in legs:
        if not isinstance(leg, list) or len(leg) != 6:
            raise SegmentContextError("Invalid journey leg")
        trip, board, start, alight, end, boarding_minute = leg
        if (
            any(not isinstance(value, str) or not 1 <= len(value) <= 200 for value in (trip, start, end))
            or any(type(value) is not int for value in (board, alight, boarding_minute))
            or not (0 <= board < alight <= 2**31 - 1)
            or not (0 <= boarding_minute <= 1439 + SEARCH_WINDOW // 60)
            or (requested_minute is not None
                and not requested_minute <= boarding_minute <= requested_minute + SEARCH_WINDOW // 60)
        ):
            raise SegmentContextError("Invalid journey leg")
        row = db.execute(text("""
            SELECT t.route_id, t.service_id, t.direction_id, r.short_name,
                   b.departure, a.arrival
            FROM trips t JOIN routes r ON r.id=t.route_id
            JOIN stop_times b ON b.trip_id=t.id
            JOIN stop_times a ON a.trip_id=t.id
            WHERE t.id=:trip AND b.stop_sequence=:board AND a.stop_sequence=:alight
              AND b.stop_id=:start AND a.stop_id=:end
              AND b.departure IS NOT NULL AND a.arrival>=b.departure
        """), dict(trip=trip, board=board, alight=alight, start=start, end=end)).first()
        if row is None:
            raise SegmentContextError("Ordered GTFS journey leg not found", 404)
        offset_minutes = boarding_minute - row.departure // 60
        offset = offset_minutes // 1440
        service_day = _date_offset(day, offset)
        if (
            offset_minutes % 1440 or not -(MAX_GTFS_HOUR // 24) <= offset <= 1
            or service_day is None or row.service_id not in active_services(db, service_day)
            or (previous_arrival is not None and row.departure + offset_minutes * 60 < previous_arrival)
        ):
            raise SegmentContextError("Journey leg does not match GTFS service on this date")
        previous_arrival = row.arrival + offset_minutes * 60
        keys.append(SegmentKey(row.route_id, _direction(row.short_name, row.direction_id),
                               start, end, service_day, boarding_minute % 1440))
    return keys
