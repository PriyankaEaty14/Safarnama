
from pathlib import Path
import pandas as pd

BASE = Path(__file__).resolve().parents[1]
DATA = BASE / "data" / "processed"
OUT = BASE / "outputs"

mapping = pd.read_csv(
    OUT / "stop_matching_report_v3.csv",
    dtype={
        "route": str,
        "ticket_stop_name": str,
        "v3_stop_id": str
    }
)

route_stops = pd.read_parquet(
    DATA / "route_stops.parquet"
)

route_stops["route"] = route_stops["route"].astype(str)
route_stops["stop_id"] = route_stops["stop_id"].astype(str)

# Only newly recovered component matches.
recovered = mapping[
    mapping["v3_method"] == "component_exact"
].copy()

# Attach GTFS stop names.
gtfs_names = (
    route_stops[
        ["route", "stop_id", "stop_name"]
    ]
    .drop_duplicates()
    .rename(columns={
        "stop_id": "v3_stop_id",
        "stop_name": "gtfs_stop_name"
    })
)

review = recovered.merge(
    gtfs_names,
    on=["route", "v3_stop_id"],
    how="left"
)

# Include frequency of each recovered name.
diagnosis = pd.read_csv(
    OUT / "unmatched_stop_diagnosis.csv",
    dtype={"route": str, "ticket_stop_name": str}
)

review = review.merge(
    diagnosis[
        ["route", "ticket_stop_name", "ticket_occurrences"]
    ],
    on=["route", "ticket_stop_name"],
    how="left",
    validate="many_to_one"
)

review = review.sort_values(
    "ticket_occurrences",
    ascending=False
)

columns = [
    "route",
    "ticket_stop_name",
    "gtfs_stop_name",
    "v3_stop_id",
    "ticket_occurrences"
]

print("TOP 25 RECOVERED STOP MAPPINGS")
print("=" * 80)
print(review[columns].head(25).to_string(index=False))

path = OUT / "v3_stop_name_review.csv"
review[columns].to_csv(path, index=False)

print("\nTotal recovered mappings:", len(recovered))
print("Saved:", path)
