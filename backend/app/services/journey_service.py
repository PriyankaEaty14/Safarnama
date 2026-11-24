"""Indexed timetable search for direct and one-transfer bus journeys."""

from bisect import bisect_left, bisect_right
from collections import defaultdict
from dataclasses import dataclass
from datetime import date
from functools import cache
from heapq import nsmallest
import json

from sqlalchemy import text


WEEKDAYS = ("monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday")
DAY_SECONDS = 86400
MAX_GTFS_HOUR = 99
SEARCH_WINDOW = 6 * 3600
MIN_TRANSFER = 180
MAX_TRANSFER = 3600


@dataclass(frozen=True)
class Boarding:
    trip: str
    sequence: int
    departure: int
    offset: int
    route_id: str
    route: str
    direction: str | None
    alight_sequence: int | None
    alight_arrival: int | None


@dataclass(frozen=True)
class LegChoice:
    board: Boarding
    alight_sequence: int
    arrival: int


def active_services(db, day: date) -> set[str]:
    day_text = day.isoformat()
    weekday = WEEKDAYS[day.weekday()]
    active = set(db.execute(text(
        f"SELECT id FROM calendars WHERE start_date<=:day AND end_date>=:day AND {weekday}=1"
    ), {"day": day_text}).scalars())
    for service_id, kind in db.execute(text(
        "SELECT service_id,exception_type FROM calendar_dates WHERE date=:day"
    ), {"day": day_text}):
        if kind == 1:
            active.add(service_id)
        else:
            active.discard(service_id)
    return active


def search_journeys(db, origin: str, destination: str, day: date, requested: int,
                    limit: int = 12, preference: str = "fastest") -> list[dict]:
    """Apply the same inclusive six-hour cutoff to every boarding."""
    deadline = requested + SEARCH_WINDOW
    max_gtfs_time = (MAX_GTFS_HOUR + 1) * 3600 - 1
    services = {}
    for relative_day in range(-(max_gtfs_time // DAY_SECONDS), deadline // DAY_SECONDS + 1):
        ordinal = day.toordinal() + relative_day
        if 1 <= ordinal <= date.max.toordinal():
            service_ids = active_services(db, date.fromordinal(ordinal))
            if service_ids:
                services[relative_day * DAY_SECONDS] = service_ids
    if not services:
        return []

    @cache
    def trip_stops(trip_id):
        return db.execute(text("""
            SELECT stop_id AS id, stop_sequence AS seq, arrival, departure
            FROM stop_times WHERE trip_id=:trip ORDER BY stop_sequence
        """), {"trip": trip_id}).all()

    def boardings(stop_id, for_destination=False):
        destination_join = """
            JOIN stop_times dest ON dest.trip_id=st.trip_id AND dest.stop_id=:destination
                AND dest.stop_sequence>st.stop_sequence AND dest.arrival>=st.departure
        """ if for_destination else ""
        destination_fields = "dest.stop_sequence, dest.arrival" if for_destination else "NULL, NULL"
        query = text(f"""
            SELECT st.trip_id, st.stop_sequence, st.departure, t.service_id,
                   t.route_id, r.short_name, t.direction_id, {destination_fields}
            FROM stop_times st JOIN trips t ON t.id=st.trip_id
            JOIN routes r ON r.id=t.route_id {destination_join}
            WHERE st.stop_id=:stop AND st.departure BETWEEN :earliest AND :latest
        """)
        options = []
        for offset, service_ids in services.items():
            if requested - offset > max_gtfs_time or deadline - offset < 0:
                continue
            rows = db.execute(query, {
                "stop": stop_id, "destination": destination,
                "earliest": requested - offset, "latest": deadline - offset,
            })
            for trip, seq, departure, service, route_id, name, direction, end_seq, arrival in rows:
                if service in service_ids:
                    options.append(Boarding(trip, seq, departure + offset, offset, route_id,
                                            name or route_id, direction, end_seq, arrival))
        return sorted(options, key=lambda item: item.departure)

    @cache
    def second_boardings(stop_id):
        options = boardings(stop_id, for_destination=True)
        return [item.departure for item in options], options

    transfers = defaultdict(dict)
    for start, end, kind, minimum in db.execute(text("SELECT * FROM transfers")):
        transfers[start][end] = (kind, minimum)

    def candidates():
        for first in boardings(origin):
            for stop in trip_stops(first.trip):
                if stop.seq <= first.sequence or stop.arrival is None:
                    continue
                arrival = stop.arrival + first.offset
                if arrival < first.departure:
                    continue
                left = LegChoice(first, stop.seq, arrival)
                if stop.id == destination:
                    yield (left,)
                    continue
                if arrival > deadline:
                    continue
                connections = {stop.id: (0, None), **transfers.get(stop.id, {})}
                for transfer_stop, (kind, minimum) in connections.items():
                    if kind == 3:
                        continue
                    wait = minimum if kind == 2 else MIN_TRANSFER
                    earliest = arrival + wait
                    latest = min(arrival + max(MAX_TRANSFER, wait), deadline)
                    if earliest > latest:
                        continue
                    departures, options = second_boardings(transfer_stop)
                    start = bisect_left(departures, earliest)
                    end = bisect_right(departures, latest)
                    for second in options[start:end]:
                        if (second.trip, second.offset) != (first.trip, first.offset):
                            yield (left, LegChoice(second, second.alight_sequence,
                                                  second.alight_arrival + second.offset))

    def rank(choices):
        departure = choices[0].board.departure // 60
        arrival = choices[-1].arrival // 60
        if preference == "balanced":
            return arrival + 10 * (len(choices) - 1), arrival, departure
        return arrival, len(choices) - 1, departure

    def build_leg(choice):
        board = choice.board
        stops = [stop for stop in trip_stops(board.trip)
                 if board.sequence <= stop.seq <= choice.alight_sequence]
        stop_ids = [stop.id for stop in stops]

        def local_minutes(seconds):
            return None if seconds is None else (seconds + board.offset) // 60

        return {
            "tripId": board.trip, "routeId": board.route_id, "route": board.route,
            "boardSequence": board.sequence, "alightSequence": choice.alight_sequence,
            "direction": board.direction, "stopIds": stop_ids,
            "stopTimes": [{"arrival": local_minutes(stop.arrival),
                           "departure": local_minutes(stop.departure)} for stop in stops],
            "start": board.departure // 60, "end": choice.arrival // 60,
            "segments": [{"from": a, "to": b, "level": None} for a, b in zip(stop_ids, stop_ids[1:])],
        }

    def distinct_choices():
        # A trip and service day identify a scheduled run. Board and alight
        # sequences identify the occurrences even when a route revisits a stop.
        seen = set()
        for choices in candidates():
            key = tuple((leg.board.trip, leg.board.offset, leg.board.sequence, leg.alight_sequence)
                        for leg in choices)
            if key not in seen:
                seen.add(key)
                yield choices

    journeys = []
    for choices in nsmallest(limit, distinct_choices(), key=rank):
        legs = [build_leg(choice) for choice in choices]
        departure, arrival = legs[0]["start"], legs[-1]["end"]
        journey_id = json.dumps([
            [leg["tripId"], leg["boardSequence"], leg["stopIds"][0],
             leg["alightSequence"], leg["stopIds"][-1], leg["start"]] for leg in legs
        ], separators=(",", ":"))
        journeys.append({
            "id": journey_id, "departure": departure, "arrival": arrival,
            "duration": arrival - departure, "transfers": len(legs) - 1,
            "transferDuration": legs[1]["start"] - legs[0]["end"] if len(legs) > 1 else 0,
            "legs": legs, "coverage": 0, "busiest": None, "confidence": None,
            "crowdingStatus": "unavailable",
            "rankingStatus": "schedule_based" if preference == "balanced" else "schedule_only",
        })
    return journeys
