
from pathlib import Path
import pandas as pd

BASE = Path(__file__).resolve().parents[1]
GTFS = BASE / "data/raw/gtfs"
OUT = BASE / "data/processed"

OUT.mkdir(parents=True, exist_ok=True)

print("Loading GTFS files...")

routes = pd.read_csv(
    GTFS / "routes.txt",
    dtype=str
)

trips = pd.read_csv(
    GTFS / "trips.txt",
    dtype=str,
    usecols=["route_id", "trip_id"]
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

stops = pd.read_csv(
    GTFS / "stops.txt",
    dtype=str,
    usecols=["stop_id", "stop_name"]
)

print("Joining GTFS tables...")

# Link scheduled trips to their route names
trip_routes = trips.merge(
    routes[["route_id", "route_short_name"]],
    on="route_id",
    how="inner"
)

# Link stop times to routes
route_stops = stop_times.merge(
    trip_routes,
    on="trip_id",
    how="inner"
)

# Add official stop names
route_stops = route_stops.merge(
    stops,
    on="stop_id",
    how="inner"
)

# Normalize route names
route_stops["route"] = (
    route_stops["route_short_name"]
    .str.upper()
    .str.strip()
)

# Retain unique route-stop combinations
route_stops = route_stops[
    ["route", "stop_id", "stop_name"]
].drop_duplicates()

route_stops.to_parquet(
    OUT / "route_stops.parquet",
    index=False
)

print("\nROUTE-STOP MAPPING COMPLETE")
print("Unique routes:", route_stops["route"].nunique())
print("Unique stops:", route_stops["stop_id"].nunique())
print("Route-stop pairs:", len(route_stops))

print("\nSample mapping:")
print(route_stops.head(15).to_string(index=False))
