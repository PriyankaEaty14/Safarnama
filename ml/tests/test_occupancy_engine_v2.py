
import pytest

from src.occupancy_engine_v2 import (
    canonical_pattern_id,
    group_patterns,
    reconstruct_load,
    select_patterns
)


def ticket(start, end, count=1):
    return {
        "start_stop_id": start,
        "end_stop_id": end,
        "passenger_count": count
    }


def test_unique_journey():
    result = reconstruct_load(
        ["A", "B", "C"],
        [ticket("A", "C", 3)]
    )

    assert result["unambiguous_passengers"] == 3
    assert result["peak_load_lower_bound"] == 3
    assert result["peak_load_upper_bound"] == 3
    assert result["mathematical_validation_passed"]


def test_repeated_boarding_stop():
    result = reconstruct_load(
        ["A", "B", "C", "B", "D"],
        [ticket("B", "D", 3)]
    )

    assert result["ambiguous_passengers"] == 3

    assert [
        row["ticket_load_lower_bound"]
        for row in result["profile"]
    ] == [0, 0, 0, 3, 0]

    assert [
        row["ticket_load_upper_bound"]
        for row in result["profile"]
    ] == [0, 3, 3, 3, 0]


def test_repeated_destination_stop():
    result = reconstruct_load(
        ["A", "B", "C", "B", "D"],
        [ticket("A", "B", 2)]
    )

    assert result["ambiguous_passengers"] == 2
    assert result["profile"][1][
        "ticket_load_lower_bound"
    ] == 0

    assert result["profile"][1][
        "ticket_load_upper_bound"
    ] == 2


def test_unmatched_stop():
    result = reconstruct_load(
        ["A", "B", "C"],
        [ticket("X", "C", 2)]
    )

    assert result["excluded_passengers"] == 2
    assert result["supported_ticketed_passengers"] == 0


def test_reverse_stop_order():
    result = reconstruct_load(
        ["A", "B", "C"],
        [ticket("C", "A", 4)]
    )

    assert result["excluded_passengers"] == 4


def test_load_balance():
    result = reconstruct_load(
        ["A", "B", "C", "D"],
        [
            ticket("A", "C", 3),
            ticket("B", "D", 2)
        ]
    )

    assert [
        row["unambiguous_ticket_load"]
        for row in result["profile"]
    ] == [3, 5, 2, 0]

    assert all(
        result["validation_checks"].values()
    )


def test_identical_trip_patterns():
    patterns = group_patterns({
        "trip_1": ["A", "B", "C"],
        "trip_2": ["A", "B", "C"]
    })

    assert len(patterns) == 1

    pattern = next(iter(patterns.values()))

    assert pattern["trip_ids"] == [
        "trip_1", "trip_2"
    ]


def test_distinct_patterns():
    assert canonical_pattern_id(
        ["A", "B", "C"]
    ) != canonical_pattern_id(
        ["A", "C", "B"]
    )


def test_invalid_pattern():
    with pytest.raises(ValueError):
        reconstruct_load(["A"], [])


def test_invalid_passenger_count():
    with pytest.raises(ValueError):
        reconstruct_load(
            ["A", "B"],
            [ticket("A", "B", -1)]
        )


def test_pattern_tie_is_preserved():
    patterns = group_patterns({
        "trip_1": ["A", "B", "C"],
        "trip_2": ["A", "X", "C"]
    })

    selected = select_patterns(
        patterns,
        [ticket("A", "C", 2)]
    )

    assert len(selected) == 2


def test_no_supported_pattern():
    patterns = group_patterns({
        "trip_1": ["A", "B", "C"]
    })

    selected = select_patterns(
        patterns,
        [ticket("X", "Y", 2)]
    )

    assert selected == []
