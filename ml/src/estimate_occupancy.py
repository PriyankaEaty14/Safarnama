
from pathlib import Path
from collections import Counter
import pandas as pd

BASE = Path(__file__).resolve().parents[1]
DATA = BASE / "data/processed"
GTFS = BASE / "data/raw/gtfs"
OUT = BASE / "outputs"
OUT.mkdir(parents=True, exist_ok=True)

RUN_ID = "DL1PD8407_48"

print("Loading selected candidate run...")

tickets = pd.read_parquet(
    DATA / "candidate_bus_runs.parquet"
)

run = tickets[
    tickets["candidate_run_id"] == RUN_ID
].copy()

if run.empty:
    raise ValueError("Selected run not found")

route = run["route"].iloc[0]

print("Run:", RUN_ID)
print("Route:", route)
print("Ticket records:", len(run))

# Load GTFS
routes = pd.read_csv(GTFS / "routes.txt", dtype=str)
trips = pd.read_csv(GTFS / "trips.txt", dtype=str)

route_ids = routes.loc[
    routes["route_short_name"].str.upper().str.strip() == route,
    "route_id"
]

route_trips = trips[
    trips["route_id"].isin(route_ids)
]["trip_id"]

stop_times = pd.read_csv(
    GTFS / "stop_times.txt",
    dtype=str,
    usecols=["trip_id", "stop_id", "stop_sequence"]
)

stop_times = stop_times[
    stop_times["trip_id"].isin(route_trips)
].copy()

stop_times["stop_sequence"] = pd.to_numeric(
    stop_times["stop_sequence"]
)

# Find GTFS pattern supporting the most tickets
best_trip = None
best_score = -1
best_stops = []

for trip_id, group in stop_times.groupby("trip_id"):
    group = group.sort_values("stop_sequence")
    stops = group["stop_id"].tolist()

    positions = {}
    for i, stop in enumerate(stops):
        positions.setdefault(stop, []).append(i)

    score = 0

    for row in run.itertuples(index=False):
        start = str(row.start_stop_id)
        end = str(row.end_stop_id)

        if start not in positions or end not in positions:
            continue

        if any(
            i < j
            for i in positions[start]
            for j in positions[end]
        ):
            score += row.passenger_count

    if score > best_score:
        best_score = score
        best_trip = trip_id
        best_stops = stops

print("Selected GTFS trip pattern:", best_trip)
print("Passengers supported:", best_score)

if best_trip is None:
    raise ValueError("No GTFS pattern found")

# Assign tickets to ordered stops
boardings = Counter()
alightings = Counter()

positions = {}
for i, stop in enumerate(best_stops):
    positions.setdefault(stop, []).append(i)

supported = 0
excluded = 0

for row in run.itertuples(index=False):
    start = str(row.start_stop_id)
    end = str(row.end_stop_id)

    possible = [
        (i, j)
        for i in positions.get(start, [])
        for j in positions.get(end, [])
        if i < j
    ]

    if not possible:
        excluded += row.passenger_count
        continue

    i, j = min(possible)

    boardings[i] += row.passenger_count
    alightings[j] += row.passenger_count
    supported += row.passenger_count

# Calculate load after each stop
load = 0
rows = []

for i, stop_id in enumerate(best_stops):
    load += boardings[i]
    load -= alightings[i]

    rows.append({
        "stop_sequence_index": i,
        "stop_id": stop_id,
        "boardings": boardings[i],
        "alightings": alightings[i],
        "ticket_observed_load": load
    })

result = pd.DataFrame(rows)

stops = pd.read_csv(
    GTFS / "stops.txt",
    dtype=str,
    usecols=["stop_id", "stop_name"]
)

result = result.merge(
    stops,
    on="stop_id",
    how="left"
)

result.to_csv(
    OUT / "sample_occupancy_profile.csv",
    index=False
)

print("\nOCCUPANCY PROFILE")
print("=" * 50)
print("Supported passengers:", supported)
print("Excluded passengers:", excluded)
print("Peak ticket-observed load:",
      result["ticket_observed_load"].max())

print(
    result[
        [
            "stop_sequence_index",
            "stop_name",
            "boardings",
            "alightings",
            "ticket_observed_load"
        ]
    ].to_string(index=False)
)

print("\nSaved sample_occupancy_profile.csv")
