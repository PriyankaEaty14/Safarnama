
"""Sensitivity analysis of heuristic candidate bus-run grouping.

Candidate runs are not verified physical bus trips.
"""

from pathlib import Path
import json
import pandas as pd

BASE = Path(__file__).resolve().parents[1]
DATA = BASE / "data" / "processed"
OUT = BASE / "outputs"

OUT.mkdir(parents=True, exist_ok=True)

THRESHOLDS = [15, 30, 45, 60, 90]


def load_datasets():

    cleaned = pd.read_parquet(
        DATA / "cleaned_tickets.parquet"
    )

    v2 = pd.read_parquet(
        DATA / "occupancy_ready_tickets.parquet"
    )

    v3_matches = pd.read_parquet(
        DATA / "validated_ticket_stops_v3.parquet"
    )

    # Avoid attaching matching results by row position.
    # Build a deterministic route + stop-name lookup.

    keys = [
        "route",
        "start_stop_name",
        "end_stop_name"
    ]

    mapping_columns = keys + [
        "start_stop_id",
        "end_stop_id",
        "valid_order"
    ]

    lookup = (
        v3_matches[mapping_columns]
        .drop_duplicates()
        .copy()
    )

    if lookup.duplicated(keys).any():
        raise ValueError(
            "Conflicting V3 journey mappings detected"
        )

    v3 = cleaned.merge(
        lookup,
        on=keys,
        how="left",
        validate="many_to_one",
        indicator=True
    )

    if len(v3) != len(cleaned):
        raise ValueError(
            "V3 merge changed ticket count"
        )

    if not v3["_merge"].eq("both").all():
        raise ValueError(
            "Some cleaned journeys have no V3 mapping"
        )

    v3 = v3.drop(columns="_merge")

    v3 = v3[
        v3["valid_order"].eq(True)
    ].copy()

    expected_v3 = int(
        v3_matches["valid_order"].eq(True).sum()
    )

    if len(v3) != expected_v3:
        raise ValueError(
            "V3 valid journey count mismatch"
        )

    return {
        "all_cleaned": cleaned,
        "v2_ordered": v2,
        "v3_ordered": v3
    }


def prepare_tickets(df):

    columns = [
        "vehicle_number",
        "route",
        "created_at",
        "passenger_count"
    ]

    df = df[columns].copy()

    df["created_at"] = pd.to_datetime(
        df["created_at"],
        errors="coerce"
    )

    valid = (
        df["vehicle_number"].notna()
        & df["route"].notna()
        & df["created_at"].notna()
        & df["passenger_count"].notna()
        & df["passenger_count"].gt(0)
    )

    excluded = int((~valid).sum())

    df = df[valid].copy()

    # Stable sorting preserves source order
    # for records with identical timestamps.

    df = df.sort_values(
        ["vehicle_number", "created_at"],
        kind="stable"
    ).reset_index(drop=True)

    groups = df.groupby(
        "vehicle_number",
        sort=False
    )

    previous_time = groups["created_at"].shift()

    previous_route = groups["route"].shift()

    gap = (
        df["created_at"] - previous_time
    ).dt.total_seconds() / 60

    mandatory_boundary = (
        previous_time.isna()
        | df["route"].ne(previous_route)
        | (
            df["created_at"].dt.normalize()
            != previous_time.dt.normalize()
        )
    ).fillna(True)

    df["gap_minutes"] = gap
    df["mandatory_boundary"] = mandatory_boundary

    return df, excluded


def analyze_threshold(df, threshold):

    new_run = (
        df["mandatory_boundary"]
        | df["gap_minutes"].gt(threshold)
    )

    # Globally unique temporary group number.

    run_id = new_run.astype("int64").cumsum()

    summary = (
        df.groupby(run_id, sort=False)
        .agg(
            ticket_count=("passenger_count", "size"),
            passengers=("passenger_count", "sum"),
            first_ticket=("created_at", "min"),
            last_ticket=("created_at", "max")
        )
    )

    duration = (
        summary["last_ticket"]
        - summary["first_ticket"]
    ).dt.total_seconds() / 60

    run_count = len(summary)

    if run_count == 0:
        raise ValueError("No candidate runs")

    if int(summary["ticket_count"].sum()) != len(df):
        raise ValueError(
            "Ticket accounting failed"
        )

    if int(summary["passengers"].sum()) != int(
        df["passenger_count"].sum()
    ):
        raise ValueError(
            "Passenger accounting failed"
        )

    singleton_count = int(
        summary["ticket_count"].eq(1).sum()
    )

    return {
        "gap_minutes": threshold,
        "ticket_records": int(len(df)),
        "ticketed_passengers": int(
            df["passenger_count"].sum()
        ),
        "candidate_runs": int(run_count),
        "mean_tickets_per_run": round(
            float(summary["ticket_count"].mean()), 4
        ),
        "median_tickets_per_run": float(
            summary["ticket_count"].median()
        ),
        "singleton_runs": singleton_count,
        "singleton_run_percentage": round(
            100 * singleton_count / run_count, 4
        ),
        "runs_with_at_least_5_tickets": int(
            summary["ticket_count"].ge(5).sum()
        ),
        "runs_with_at_least_10_tickets": int(
            summary["ticket_count"].ge(10).sum()
        ),
        "median_duration_minutes": round(
            float(duration.median()), 4
        ),
        "p90_duration_minutes": round(
            float(duration.quantile(0.90)), 4
        ),
        "max_duration_minutes": round(
            float(duration.max()), 4
        ),
        "physical_trip_verified": False
    }


def main():

    datasets = load_datasets()

    results = []

    for name, source in datasets.items():

        print("\n" + "=" * 65)
        print("DATASET:", name)
        print("Input ticket records:", len(source))

        prepared, excluded = prepare_tickets(source)

        print("Excluded invalid records:", excluded)

        dataset_results = []

        for threshold in THRESHOLDS:

            result = analyze_threshold(
                prepared,
                threshold
            )

            result["dataset"] = name
            result["excluded_invalid_records"] = excluded

            dataset_results.append(result)

            print(
                f"Gap: {threshold:>2} min",
                "| Runs:", result["candidate_runs"],
                "| Median tickets:",
                result["median_tickets_per_run"],
                "| Singletons:",
                result["singleton_run_percentage"],
                "%"
            )

        baseline = next(
            row["candidate_runs"]
            for row in dataset_results
            if row["gap_minutes"] == 45
        )

        counts = [
            row["candidate_runs"]
            for row in dataset_results
        ]

        # Increasing the threshold must not
        # increase the number of groups.

        if any(
            counts[i] < counts[i + 1]
            for i in range(len(counts) - 1)
        ):
            raise ValueError(
                "Candidate-run monotonicity failed"
            )

        for row in dataset_results:

            row["run_count_change_vs_45min_pct"] = round(
                100 * (
                    row["candidate_runs"] - baseline
                ) / baseline,
                4
            )

        results.extend(dataset_results)

    report = pd.DataFrame(results)

    report.to_csv(
        OUT / "candidate_run_sensitivity_v2.csv",
        index=False
    )

    metadata = {
        "schema_version": "2.0",
        "thresholds_minutes": THRESHOLDS,
        "datasets": list(datasets.keys()),
        "baseline_threshold_minutes": 45,
        "physical_trip_verified": False,
        "grouping_method": [
            "Vehicle identity",
            "Chronological ticket timestamps",
            "Route change boundary",
            "Calendar date boundary",
            "Ticket gap threshold"
        ],
        "limitations": [
            "Ticket timestamps may represent issuance time.",
            "Candidate groups are not verified bus trips.",
            "Calendar dates are not GTFS service dates.",
            "Unmatched ticket exclusions can change boundaries.",
            "Equal timestamps may have uncertain event order.",
            "No threshold is validated against physical trips.",
            "Stop order and GPS continuity are not verified.",
            "No occupancy or seat availability is inferred."
        ],
        "results": results
    }

    (OUT / "candidate_run_sensitivity_v2.json").write_text(
        json.dumps(
            metadata,
            indent=2,
            allow_nan=False
        ),
        encoding="utf-8"
    )

    print("\nFINAL SENSITIVITY RESULTS")
    print("=" * 65)

    columns = [
        "dataset",
        "gap_minutes",
        "candidate_runs",
        "median_tickets_per_run",
        "singleton_run_percentage",
        "runs_with_at_least_10_tickets",
        "run_count_change_vs_45min_pct"
    ]

    print(
        report[columns].to_string(index=False)
    )

    print("\nTicket accounting: PASSED")
    print("Passenger accounting: PASSED")
    print("Threshold monotonicity: PASSED")
    print("Physical trip validation: NOT ESTABLISHED")
    print("Sensitivity analysis completed.")


if __name__ == "__main__":
    main()
