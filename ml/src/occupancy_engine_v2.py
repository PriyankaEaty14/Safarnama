
"""GTFS-pattern-based ticket load reconstruction.

This module does not validate physical bus trips or actual occupancy.
"""

from collections import defaultdict
import hashlib
import json
import math


def canonical_pattern_id(stops):
    stops = tuple(str(stop) for stop in stops)

    if len(stops) < 2:
        raise ValueError("A pattern requires at least two stops")

    payload = json.dumps(
        stops,
        ensure_ascii=False,
        separators=(",", ":")
    )

    return hashlib.sha256(
        payload.encode("utf-8")
    ).hexdigest()


def stop_positions(stops):
    positions = defaultdict(list)

    for index, stop in enumerate(stops):
        positions[str(stop)].append(index)

    return positions


def feasible_pairs(positions, start, end):
    return [
        (i, j)
        for i in positions.get(str(start), [])
        for j in positions.get(str(end), [])
        if i < j
    ]


def passenger_count(value):
    count = float(value)

    if (
        not math.isfinite(count)
        or count <= 0
        or not count.is_integer()
    ):
        raise ValueError("Invalid passenger count")

    return int(count)


def group_patterns(trip_sequences):
    patterns = {}

    for trip_id, stops in trip_sequences.items():
        stops = tuple(str(stop) for stop in stops)

        if len(stops) < 2:
            continue

        pattern_id = canonical_pattern_id(stops)

        if pattern_id not in patterns:
            patterns[pattern_id] = {
                "pattern_id": pattern_id,
                "stops": stops,
                "trip_ids": []
            }

        patterns[pattern_id]["trip_ids"].append(
            str(trip_id)
        )

    for pattern in patterns.values():
        pattern["trip_ids"].sort()

    return patterns


def reconstruct_load(stops, tickets):
    stops = tuple(str(stop) for stop in stops)

    if len(stops) < 2:
        raise ValueError("Invalid GTFS pattern")

    n = len(stops)
    positions = stop_positions(stops)

    boardings = [0] * n
    alightings = [0] * n
    lower = [0] * n
    upper = [0] * n

    total = 0
    unique = 0
    ambiguous = 0
    excluded = 0

    for ticket in tickets:
        count = passenger_count(
            ticket["passenger_count"]
        )

        total += count

        pairs = feasible_pairs(
            positions,
            ticket["start_stop_id"],
            ticket["end_stop_id"]
        )

        if not pairs:
            excluded += count
            continue

        if len(pairs) == 1:
            i, j = pairs[0]

            boardings[i] += count
            alightings[j] += count
            unique += count

        else:
            ambiguous += count

        # Segment-wise feasible bounds.
        # A passenger is aboard after stop k
        # when boarding <= k < alighting.

        for k in range(n):
            active = [
                i <= k < j
                for i, j in pairs
            ]

            if all(active):
                lower[k] += count

            if any(active):
                upper[k] += count

    profile = []
    unique_load = 0

    for k, stop in enumerate(stops):
        unique_load += boardings[k]
        unique_load -= alightings[k]

        profile.append({
            "stop_sequence_index": k,
            "stop_id": stop,
            "unambiguous_boardings": boardings[k],
            "unambiguous_alightings": alightings[k],
            "unambiguous_ticket_load": unique_load,
            "ticket_load_lower_bound": lower[k],
            "ticket_load_upper_bound": upper[k]
        })

    checks = {
        "passenger_accounting": (
            total == unique + ambiguous + excluded
        ),
        "unique_boarding_balance": (
            sum(boardings) == unique
        ),
        "unique_alighting_balance": (
            sum(alightings) == unique
        ),
        "terminal_load_zero": (
            unique_load == 0
            and lower[-1] == 0
            and upper[-1] == 0
        ),
        "valid_segment_bounds": all(
            0 <= lo <= hi <= unique + ambiguous
            for lo, hi in zip(lower, upper)
        ),
        "unique_load_nonnegative": all(
            0 <= row["unambiguous_ticket_load"]
            <= row["ticket_load_lower_bound"]
            for row in profile
        )
    }

    if not all(checks.values()):
        raise ValueError(
            f"Load balance failed: {checks}"
        )

    return {
        "pattern_id": canonical_pattern_id(stops),
        "stop_count": n,
        "total_ticketed_passengers": total,
        "supported_ticketed_passengers": (
            unique + ambiguous
        ),
        "unambiguous_passengers": unique,
        "ambiguous_passengers": ambiguous,
        "excluded_passengers": excluded,
        "peak_load_lower_bound": max(lower),
        "peak_load_upper_bound": max(upper),
        "mathematical_validation_passed": True,
        "validation_checks": checks,
        "physical_trip_verified": False,
        "actual_bus_occupancy_verified": False,
        "is_live": False,
        "profile": profile
    }


def select_patterns(patterns, tickets):
    tickets = list(tickets)
    candidates = []

    for pattern_id, pattern in patterns.items():
        positions = stop_positions(
            pattern["stops"]
        )

        supported = 0

        for ticket in tickets:
            pairs = feasible_pairs(
                positions,
                ticket["start_stop_id"],
                ticket["end_stop_id"]
            )

            if pairs:
                supported += passenger_count(
                    ticket["passenger_count"]
                )

        candidates.append({
            "pattern_id": pattern_id,
            "supported_passengers": supported,
            "stops": pattern["stops"],
            "trip_ids": pattern["trip_ids"]
        })

    if not candidates:
        return []

    best_score = max(
        row["supported_passengers"]
        for row in candidates
    )

    if best_score == 0:
        return []

    return sorted(
        [
            row for row in candidates
            if row["supported_passengers"] == best_score
        ],
        key=lambda row: row["pattern_id"]
    )
