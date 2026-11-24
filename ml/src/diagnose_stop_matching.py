
from pathlib import Path
import pandas as pd

BASE = Path(__file__).resolve().parents[1]
DATA = BASE / "data" / "processed"
OUT = BASE / "outputs"

print("Loading matching results...")

mapping = pd.read_csv(
    OUT / "stop_matching_report_v2.csv",
    dtype={"route": str, "ticket_stop_name": str}
)

tickets = pd.read_parquet(
    DATA / "cleaned_tickets.parquet",
    columns=[
        "route",
        "start_stop_name",
        "end_stop_name"
    ]
)

# Count stop-name occurrences in both columns.
boarding = tickets[
    ["route", "start_stop_name"]
].rename(
    columns={"start_stop_name": "ticket_stop_name"}
)

destination = tickets[
    ["route", "end_stop_name"]
].rename(
    columns={"end_stop_name": "ticket_stop_name"}
)

all_stops = pd.concat(
    [boarding, destination],
    ignore_index=True
)

frequency = (
    all_stops
    .groupby(
        ["route", "ticket_stop_name"],
        dropna=False
    )
    .size()
    .reset_index(name="ticket_occurrences")
)

# Attach occurrence counts to the existing mapping.
diagnosis = mapping.merge(
    frequency,
    on=["route", "ticket_stop_name"],
    how="left",
    validate="one_to_one"
)

diagnosis["ticket_occurrences"] = (
    diagnosis["ticket_occurrences"]
    .fillna(0)
    .astype(int)
)

print("\nMATCHING METHOD DISTRIBUTION")
print("=" * 55)

print(
    diagnosis.groupby("method", dropna=False).agg(
        unique_route_stop_names=(
            "ticket_stop_name", "size"
        ),
        ticket_occurrences=(
            "ticket_occurrences", "sum"
        )
    ).to_string()
)

# Missing or ambiguous matches.
failed = diagnosis[
    diagnosis["stop_id"].isna()
].copy()

failed = failed.sort_values(
    "ticket_occurrences",
    ascending=False
)

print("\nTOP 30 UNMATCHED ROUTE-STOP NAMES")
print("=" * 55)

print(
    failed[
        [
            "route",
            "ticket_stop_name",
            "method",
            "ticket_occurrences"
        ]
    ].head(30).to_string(index=False)
)

# Summarize which routes are most affected.
route_failures = (
    failed.groupby("route", dropna=False)
    .agg(
        unmatched_unique_names=(
            "ticket_stop_name", "size"
        ),
        unmatched_occurrences=(
            "ticket_occurrences", "sum"
        )
    )
    .sort_values(
        "unmatched_occurrences",
        ascending=False
    )
    .reset_index()
)

print("\nTOP 20 ROUTES BY UNMATCHED STOP OCCURRENCES")
print("=" * 55)
print(route_failures.head(20).to_string(index=False))

failed.to_csv(
    OUT / "unmatched_stop_diagnosis.csv",
    index=False
)

route_failures.to_csv(
    OUT / "route_matching_failures.csv",
    index=False
)

print("\nSaved:")
print(OUT / "unmatched_stop_diagnosis.csv")
print(OUT / "route_matching_failures.csv")
print("\nDIAGNOSIS COMPLETE")
