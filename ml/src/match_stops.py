
from pathlib import Path
import pandas as pd
import re

BASE = Path(__file__).resolve().parents[1]

GTFS = BASE / "data" / "raw" / "gtfs"
DATA = BASE / "data" / "processed"
OUT = BASE / "outputs"

OUT.mkdir(parents=True, exist_ok=True)

print("Loading ticket stops...")

tickets = pd.read_parquet(
    DATA / "cleaned_tickets.parquet",
    columns=[
        "route",
        "start_stop_name",
        "end_stop_name",
        "passenger_count"
    ]
)

print("Loading GTFS stops...")

stops = pd.read_csv(
    GTFS / "stops.txt",
    dtype=str
)

# Standardize names without changing their meaning
def normalize(name):
    if pd.isna(name):
        return ""

    name = str(name).upper().strip()
    name = re.sub(r"\s+", " ", name)

    return name

stops["normalized"] = (
    stops["stop_name"].map(normalize)
)

tickets["start_normalized"] = (
    tickets["start_stop_name"].map(normalize)
)

tickets["end_normalized"] = (
    tickets["end_stop_name"].map(normalize)
)

# Some GTFS names refer to multiple stop IDs.
# Keep only unambiguous exact matches.
unique_stops = (
    stops.groupby("normalized")
    .agg(
        stop_id=("stop_id", "first"),
        id_count=("stop_id", "nunique")
    )
    .reset_index()
)

unique_stops = unique_stops[
    unique_stops["id_count"] == 1
]

stop_map = dict(
    zip(
        unique_stops["normalized"],
        unique_stops["stop_id"]
    )
)

tickets["start_stop_id"] = (
    tickets["start_normalized"].map(stop_map)
)

tickets["end_stop_id"] = (
    tickets["end_normalized"].map(stop_map)
)

start_matched = tickets["start_stop_id"].notna()
end_matched = tickets["end_stop_id"].notna()
both_matched = start_matched & end_matched

print("\nMATCHING RESULTS")
print("=" * 45)

print("Total tickets:", len(tickets))

print(
    "Boarding stop matches:",
    start_matched.sum(),
    f"({start_matched.mean():.2%})"
)

print(
    "Destination stop matches:",
    end_matched.sum(),
    f"({end_matched.mean():.2%})"
)

print(
    "Both stops matched:",
    both_matched.sum(),
    f"({both_matched.mean():.2%})"
)

# Save unmatched boarding names for inspection
unmatched_start = (
    tickets.loc[
        ~start_matched,
        "start_stop_name"
    ]
    .value_counts()
    .head(100)
)

unmatched_start.to_csv(
    OUT / "unmatched_boarding_stops.csv"
)

# Save unmatched destination names
unmatched_end = (
    tickets.loc[
        ~end_matched,
        "end_stop_name"
    ]
    .value_counts()
    .head(100)
)

unmatched_end.to_csv(
    OUT / "unmatched_destination_stops.csv"
)

# Save stop mapping results
tickets.to_parquet(
    DATA / "matched_ticket_stops.parquet",
    index=False
)

print("\nSaved matched ticket stops.")
print("Saved unmatched stop reports.")
