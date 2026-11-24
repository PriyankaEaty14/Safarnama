
"""Reproducible multi-run ticket-derived load reconstruction."""

from pathlib import Path
from collections import defaultdict
import argparse
import hashlib
import json
import pandas as pd

from occupancy_engine_v2 import (
    canonical_pattern_id,
    group_patterns,
    reconstruct_load,
    select_patterns
)

BASE = Path(__file__).resolve().parents[1]
DATA = BASE / "data" / "processed"
GTFS = BASE / "data" / "raw" / "gtfs"
OUT = BASE / "outputs"

OUT.mkdir(parents=True, exist_ok=True)


def save_json(path, content):
    path.write_text(
        json.dumps(
            content,
            indent=2,
            ensure_ascii=False,
            allow_nan=False
        ),
        encoding="utf-8"
    )


def file_hash(path):
    digest = hashlib.sha256()

    with path.open("rb") as file:
        for chunk in iter(
            lambda: file.read(1024 * 1024), b""
        ):
            digest.update(chunk)

    return digest.hexdigest()


def load_gtfs_patterns(required_routes):

    routes = pd.read_csv(
        GTFS / "routes.txt",
        dtype=str
    )

    trips = pd.read_csv(
        GTFS / "trips.txt",
        dtype=str
    )

    routes["route"] = (
        routes["route_short_name"]
        .str.upper()
        .str.strip()
    )

    routes = routes[
        routes["route"].isin(required_routes)
    ]

    route_trips = trips.merge(
        routes[["route_id", "route"]],
        on="route_id",
        how="inner"
    )

    stop_times = pd.read_csv(
        GTFS / "stop_times.txt",
        dtype=str,
        usecols=[
            "trip_id",
            "stop_id",
            "stop_sequence"
        ]
    )

    stop_times = stop_times[
        stop_times["trip_id"].isin(
            route_trips["trip_id"]
        )
    ].copy()

    stop_times["stop_sequence"] = pd.to_numeric(
        stop_times["stop_sequence"],
        errors="coerce"
    )

    sequences = {}
    invalid_trips = []

    for trip_id, group in stop_times.groupby(
        "trip_id", sort=True
    ):

        invalid = (
            len(group) < 2
            or group["stop_id"].isna().any()
            or group["stop_sequence"].isna().any()
            or group["stop_sequence"].duplicated().any()
            or (group["stop_sequence"] < 0).any()
            or (
                group["stop_sequence"] % 1 != 0
            ).any()
        )

        if invalid:
            invalid_trips.append(str(trip_id))
            continue

        sequences[str(trip_id)] = tuple(
            group.sort_values(
                "stop_sequence"
            )["stop_id"].astype(str)
        )

    by_route = defaultdict(dict)

    for row in route_trips.itertuples(index=False):
        trip_id = str(row.trip_id)

        if trip_id in sequences:
            by_route[row.route][trip_id] = (
                sequences[trip_id]
            )

    patterns = {
        route: group_patterns(trip_sequences)
        for route, trip_sequences in by_route.items()
    }

    return patterns, sequences, invalid_trips


def compare_legacy_patterns(sequences):

    trip_a = "2171_FULL_19_01"
    trip_b = "2171_FULL_04_40"

    stops_a = sequences.get(trip_a)
    stops_b = sequences.get(trip_b)

    available = (
        stops_a is not None
        and stops_b is not None
    )

    return {
        "legacy_trip_a": trip_a,
        "legacy_trip_b": trip_b,
        "comparison_available": available,
        "identical_ordered_stop_sequences": (
            stops_a == stops_b
            if available else None
        ),
        "trip_a_pattern_id": (
            canonical_pattern_id(stops_a)
            if stops_a else None
        ),
        "trip_b_pattern_id": (
            canonical_pattern_id(stops_b)
            if stops_b else None
        ),
        "trip_a_stop_count": (
            len(stops_a) if stops_a else None
        ),
        "trip_b_stop_count": (
            len(stops_b) if stops_b else None
        ),
        "physical_trip_verified": False
    }


def main():

    parser = argparse.ArgumentParser()

    parser.add_argument(
        "--max-runs",
        type=int,
        default=20
    )

    parser.add_argument(
        "--min-tickets",
        type=int,
        default=10
    )

    parser.add_argument(
        "--run-id",
        action="append",
        default=[]
    )

    args = parser.parse_args()

    if args.max_runs < 1 or args.min_tickets < 1:
        parser.error(
            "Run and ticket limits must be positive"
        )

    source_path = DATA / "candidate_bus_runs.parquet"

    print("Loading candidate runs...")

    tickets = pd.read_parquet(source_path)

    required = {
        "candidate_run_id",
        "route",
        "start_stop_id",
        "end_stop_id",
        "passenger_count",
        "created_at"
    }

    missing = required - set(tickets.columns)

    if missing:
        raise ValueError(
            f"Missing columns: {sorted(missing)}"
        )

    run_summary = (
        tickets.groupby("candidate_run_id")
        .agg(
            ticket_records=("passenger_count", "size"),
            route=("route", "first"),
            route_count=("route", "nunique"),
            passengers=("passenger_count", "sum")
        )
        .reset_index()
    )

    eligible = run_summary[
        (run_summary["ticket_records"] >= args.min_tickets)
        & (run_summary["route_count"] == 1)
    ].sort_values(
        ["ticket_records", "candidate_run_id"],
        ascending=[False, True]
    )

    # Prefer route diversity in the demonstration.
    selected = (
        eligible.drop_duplicates("route")
        .head(args.max_runs)["candidate_run_id"]
        .tolist()
    )

    selected = list(
        dict.fromkeys(args.run_id + selected)
    )

    if not selected:
        raise ValueError("No eligible candidate runs")

    missing_runs = set(selected) - set(
        run_summary["candidate_run_id"]
    )

    if missing_runs:
        raise ValueError(
            f"Requested runs not found: {missing_runs}"
        )

    subset = tickets[
        tickets["candidate_run_id"].isin(selected)
    ].copy()

    required_routes = set(
        subset["route"].unique()
    )

    # Include the legacy route for the pattern audit.
    required_routes.add("717AUP")

    print("Loading GTFS patterns...")

    patterns, sequences, invalid_trips = (
        load_gtfs_patterns(required_routes)
    )

    comparison = compare_legacy_patterns(sequences)

    save_json(
        OUT / "legacy_pattern_comparison_v2.json",
        comparison
    )

    print("\nLEGACY PATTERN COMPARISON")
    print(json.dumps(comparison, indent=2))

    stops = pd.read_csv(
        GTFS / "stops.txt",
        dtype=str,
        usecols=["stop_id", "stop_name"]
    )

    if stops["stop_id"].duplicated().any():
        raise ValueError("Duplicate GTFS stop IDs")

    stop_names = stops.set_index(
        "stop_id"
    )["stop_name"].fillna("").to_dict()

    all_summaries = []
    all_profiles = []

    print("\nRECONSTRUCTING CANDIDATE RUNS")

    for run_id, run in subset.groupby(
        "candidate_run_id", sort=True
    ):

        if run["route"].nunique() != 1:
            raise ValueError(
                f"Mixed routes in candidate run {run_id}"
            )

        route = str(run["route"].iloc[0])

        records = run[
            [
                "start_stop_id",
                "end_stop_id",
                "passenger_count"
            ]
        ].to_dict("records")

        route_patterns = patterns.get(route, {})

        best_patterns = select_patterns(
            route_patterns,
            records
        )

        summary = {
            "candidate_run_id": str(run_id),
            "route": route,
            "ticket_records": int(len(run)),
            "total_ticketed_passengers": int(
                run["passenger_count"].sum()
            ),
            "matching_version": "V2",
            "candidate_run_gap_minutes": 45,
            "first_ticket": (
                run["created_at"].min().isoformat()
            ),
            "last_ticket": (
                run["created_at"].max().isoformat()
            ),
            "available_route_patterns": len(
                route_patterns
            ),
            "equally_supported_patterns": len(
                best_patterns
            ),
            "physical_trip_verified": False,
            "actual_bus_occupancy_verified": False,
            "is_live": False,
            "patterns": []
        }

        if not best_patterns:
            summary["status"] = "no_supported_pattern"

        elif len(best_patterns) == 1:
            summary["status"] = "unique_best_pattern"

        else:
            summary["status"] = "ambiguous_best_pattern"

        for pattern in best_patterns:

            result = reconstruct_load(
                pattern["stops"],
                records
            )

            profile = result.pop("profile")

            result["scheduled_trip_ids"] = (
                pattern["trip_ids"]
            )

            result["scheduled_trip_count"] = len(
                pattern["trip_ids"]
            )

            summary["patterns"].append(result)

            for row in profile:
                all_profiles.append({
                    "candidate_run_id": str(run_id),
                    "route": route,
                    "pattern_id": result["pattern_id"],
                    "stop_name": stop_names.get(
                        row["stop_id"], ""
                    ),
                    **row
                })

        all_summaries.append(summary)

        print(
            run_id,
            route,
            "| tickets:", len(run),
            "| best patterns:", len(best_patterns),
            "| status:", summary["status"]
        )

    manifest = {
        "schema_version": "2.0",
        "metric": "conditional_ticket_derived_load",
        "matching_version": "V2",
        "candidate_run_method": (
            "vehicle_route_calendar_date_45_minute_gap"
        ),
        "source_file": source_path.name,
        "source_sha256": file_hash(source_path),
        "gtfs_sha256": {
            filename: file_hash(GTFS / filename)
            for filename in [
                "routes.txt",
                "trips.txt",
                "stop_times.txt",
                "stops.txt"
            ]
        },
        "selection_method": (
            "highest ticket count per route; "
            "explicit run IDs also included"
        ),
        "minimum_tickets_for_automatic_selection": (
            args.min_tickets
        ),
        "maximum_automatically_selected_runs": (
            args.max_runs
        ),
        "requested_run_ids": args.run_id,
        "candidate_runs_analyzed": len(all_summaries),
        "invalid_gtfs_trips_excluded": len(invalid_trips),
        "physical_trip_verified": False,
        "actual_bus_occupancy_verified": False,
        "limitations": [
            "Candidate runs are heuristic ticket groups.",
            "Scheduled trip IDs do not identify actual trips.",
            "GTFS service calendar is not validated.",
            "Pattern selection uses supported passengers.",
            "Bounds are conditional on each candidate pattern.",
            "Excluded tickets are not represented in loads.",
            "Bounds are not statistical confidence intervals.",
            "No live occupancy or seat availability is inferred."
        ],
        "legacy_pattern_comparison": comparison,
        "runs": all_summaries
    }

    save_json(
        OUT / "multi_run_occupancy_summary_v2.json",
        manifest
    )

    profile_columns = [
        "candidate_run_id",
        "route",
        "pattern_id",
        "stop_name",
        "stop_sequence_index",
        "stop_id",
        "unambiguous_boardings",
        "unambiguous_alightings",
        "unambiguous_ticket_load",
        "ticket_load_lower_bound",
        "ticket_load_upper_bound"
    ]

    pd.DataFrame(
        all_profiles,
        columns=profile_columns
    ).to_csv(
        OUT / "multi_run_occupancy_profiles_v2.csv",
        index=False
    )

    # Generate sample and validation summaries
    # from exactly the same in-memory result.

    for run_id in args.run_id:

        sample = next(
            row for row in all_summaries
            if row["candidate_run_id"] == run_id
        )

        sample_report = {
            "schema_version": "2.0",
            "source": (
                "multi_run_occupancy_summary_v2.json"
            ),
            **sample
        }

        validation_report = {
            **sample_report,
            "mathematical_validation_passed": (
                bool(sample["patterns"])
                and all(
                    p["mathematical_validation_passed"]
                    for p in sample["patterns"]
                )
            ),
            "legacy_pattern_comparison": comparison
        }

        # Use a safe deterministic filename.
        tag = hashlib.sha256(
            run_id.encode("utf-8")
        ).hexdigest()[:12]

        save_json(
            OUT / f"sample_occupancy_summary_v2_{tag}.json",
            sample_report
        )

        save_json(
            OUT / f"occupancy_validation_summary_v2_{tag}.json",
            validation_report
        )

    print("\nFINAL RECONSTRUCTION SUMMARY")
    print("=" * 55)
    print("Candidate runs analyzed:", len(all_summaries))

    for status in [
        "unique_best_pattern",
        "ambiguous_best_pattern",
        "no_supported_pattern"
    ]:
        count = sum(
            row["status"] == status
            for row in all_summaries
        )

        print(status + ":", count)

    print("Profile rows:", len(all_profiles))
    print("Invalid GTFS trips excluded:", len(invalid_trips))
    print("Physical trips verified: 0")
    print("Actual occupancy verified: False")
    print("\nSaved versioned reconstruction reports.")


if __name__ == "__main__":
    main()
