
from pathlib import Path
import pandas as pd

BASE = Path(__file__).resolve().parents[1]
GTFS = BASE / "data" / "raw" / "gtfs"

required_files = [
    "stops.txt",
    "routes.txt",
    "trips.txt",
    "stop_times.txt"
]

print("=" * 55)
print("CROWDWISE - GTFS DATA INSPECTION")
print("=" * 55)

tables = {}

# Step 1: Read GTFS files
for filename in required_files:
    path = GTFS / filename

    if not path.exists():
        print("MISSING FILE:", filename)
        continue

    df = pd.read_csv(path, dtype=str)
    tables[filename] = df

    print(f"\nFILE: {filename}")
    print("Rows:", len(df))
    print("Columns:", df.columns.tolist())

    print("\nFirst 5 rows:")
    print(df.head().to_string(index=False))

    print("\nMissing values:")
    print(df.isnull().sum().to_string())

# Step 2: Check route coverage
if "routes.txt" in tables:
    routes = tables["routes.txt"]

    print("\n" + "=" * 55)
    print("GTFS ROUTE INFORMATION")
    print("=" * 55)

    if "route_short_name" in routes.columns:
        print("\nAvailable route names:")
        print(
            routes["route_short_name"]
            .dropna()
            .unique()[:30]
        )

# Step 3: Check stop coverage
if "stops.txt" in tables:
    stops = tables["stops.txt"]

    print("\nTotal GTFS stops:", len(stops))

    if "stop_name" in stops.columns:
        print("\nSample stop names:")
        print(stops["stop_name"].head(15).to_string(index=False))

# Step 4: Check trip and stop-time coverage
if (
    "trips.txt" in tables
    and "stop_times.txt" in tables
):
    trips = tables["trips.txt"]
    stop_times = tables["stop_times.txt"]

    print("\nTotal scheduled trips:", len(trips))
    print("Total stop-time records:", len(stop_times))

    if "trip_id" in stop_times.columns:
        print(
            "Trips represented in stop_times:",
            stop_times["trip_id"].nunique()
        )

# Step 5: Compare with cleaned ticket routes
ticket_file = (
    BASE / "data" / "processed"
    / "cleaned_tickets.parquet"
)

if ticket_file.exists() and "routes.txt" in tables:
    tickets = pd.read_parquet(
        ticket_file,
        columns=["route"]
    )

    routes = tables["routes.txt"]

    if "route_short_name" in routes.columns:
        ticket_routes = set(
            tickets["route"]
            .dropna()
            .astype(str)
            .str.strip()
            .str.upper()
        )

        gtfs_routes = set(
            routes["route_short_name"]
            .dropna()
            .astype(str)
            .str.strip()
            .str.upper()
        )

        common = ticket_routes & gtfs_routes

        print("\n" + "=" * 55)
        print("TICKET VS GTFS ROUTE COMPARISON")
        print("=" * 55)

        print("Ticket routes:", len(ticket_routes))
        print("GTFS routes:", len(gtfs_routes))
        print("Exact matches:", len(common))

        print("\nMatching routes:")
        print(sorted(common)[:30])

        print("\nTicket routes without exact match:")
        print(sorted(ticket_routes - gtfs_routes)[:30])

print("\nGTFS inspection completed!")
