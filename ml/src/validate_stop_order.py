
from pathlib import Path
from collections import defaultdict
import pandas as pd

BASE = Path(__file__).resolve().parents[1]
GTFS = BASE / "data/raw/gtfs"
DATA = BASE / "data/processed"
OUT = BASE / "outputs"
OUT.mkdir(parents=True, exist_ok=True)

print("Loading GTFS routes and trips...")

routes = pd.read_csv(
    GTFS / "routes.txt",
    dtype=str,
    usecols=["route_id", "route_short_name"]
)

trips = pd.read_csv(
    GTFS / "trips.txt",
    dtype=str,
    usecols=["route_id", "trip_id"]
)

print("Loading stop sequences...")

stop_times = pd.read_csv(
    GTFS / "stop_times.txt",
    dtype=str,
    usecols=["trip_id", "stop_id", "stop_sequence"]
)

stop_times["stop_sequence"] = pd.to_numeric(
    stop_times["stop_sequence"],
    errors="coerce"
)

# Map each trip to its route
trip_routes = trips.merge(
    routes,
    on="route_id",
    how="inner"
)

trip_routes["route"] = (
    trip_routes["route_short_name"]
    .str.upper()
    .str.strip()
)

# Build ordered stop sequences for each trip
ordered = stop_times.merge(
    trip_routes[["trip_id", "route"]],
    on="trip_id",
    how="inner"
)

ordered = ordered.dropna(
    subset=["stop_sequence"]
).sort_values(["trip_id", "stop_sequence"])

# Deduplicate identical stop sequences
sequences = defaultdict(set)

for (route, trip_id), group in ordered.groupby(
    ["route", "trip_id"],
    sort=False
):
    stops = tuple(group["stop_id"].tolist())
    sequences[route].add(stops)

print("Routes with stop sequences:", len(sequences))

print("Loading matched ticket stops...")

tickets = pd.read_parquet(
    DATA / "matched_ticket_stops_v2.parquet"
)

# Validate unique route / boarding / destination pairs
pairs = tickets[
    ["route", "start_stop_id", "end_stop_id"]
].dropna().drop_duplicates().copy()

print("Unique stop pairs to validate:", len(pairs))

# Precompute valid ordered pairs from GTFS sequences
print("Building valid boarding-destination pairs...")

valid_pairs = defaultdict(set)

for route, trip_sequences in sequences.items():
    for stops in trip_sequences:
        for i in range(len(stops)):
            for j in range(i + 1, len(stops)):
                if stops[i] != stops[j]:
                    valid_pairs[route].add(
                        (stops[i], stops[j])
                    )

# Check whether each pair is served in the right order
pairs["valid_order"] = [
    (start, end) in valid_pairs.get(route, set())
    for route, start, end in pairs[
        ["route", "start_stop_id", "end_stop_id"]
    ].itertuples(index=False, name=None)
]

tickets = tickets.merge(
    pairs,
    on=["route", "start_stop_id", "end_stop_id"],
    how="left"
)

tickets["valid_order"] = (
    tickets["valid_order"]
    .fillna(False)
    .astype(bool)
)

print("\nSTOP ORDER VALIDATION RESULTS")
print("=" * 45)

print("Total tickets:", len(tickets))

print(
    "Both stops matched:",
    (
        tickets["start_stop_id"].notna()
        & tickets["end_stop_id"].notna()
    ).sum()
)

print(
    "Valid ordered journeys:",
    tickets["valid_order"].sum()
)

print(
    "Valid percentage:",
    f"{tickets['valid_order'].mean():.2%}"
)

tickets.to_parquet(
    DATA / "validated_ticket_stops.parquet",
    index=False
)

print("\nSaved validated_ticket_stops.parquet")
