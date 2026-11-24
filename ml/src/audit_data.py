
from pathlib import Path
import pandas as pd

BASE = Path(__file__).resolve().parents[1]

DATA = BASE / "data" / "processed"

df = pd.read_parquet(
    DATA / "cleaned_tickets.parquet"
)

print("=" * 55)
print("CROWDWISE - DATA QUALITY AUDIT")
print("=" * 55)

# 1. Dataset overview
print("\n1. DATASET OVERVIEW")

print("Total records:", len(df))
print("Total passengers:", df["passenger_count"].sum())
print("Unique routes:", df["route"].nunique())
print("Unique vehicles:", df["vehicle_number"].nunique())

print("\nDate range:")
print(df["created_at"].min())
print(df["created_at"].max())

print("\nRecords per date:")
print(
    df.groupby(df["created_at"].dt.date)
    .size()
    .to_string()
)

# 2. Rejected records
print("\n2. REJECTED RECORDS")

rejected_file = DATA / "rejected_tickets.parquet"

if rejected_file.exists():
    rejected = pd.read_parquet(rejected_file)

    print("Rejected records:", len(rejected))

    if len(rejected) > 0:
        print("\nMissing values in rejected records:")
        print(
            rejected[
                [
                    "passenger_count",
                    "vehicle_number",
                    "route",
                    "start_stop_name",
                    "created_at"
                ]
            ].isna().sum()
        )

        print("\nInvalid passenger counts:")
        counts = pd.to_numeric(
            rejected["passenger_count"],
            errors="coerce"
        )

        print("Missing/non-numeric:", counts.isna().sum())
        print("Zero/negative:", (counts <= 0).sum())
        print(
            "Fractional:",
            ((counts % 1 != 0) & counts.notna()).sum()
        )

# 3. Route analysis
print("\n3. TOP ROUTES BY PASSENGER COUNT")

print(
    df.groupby("route")["passenger_count"]
    .sum()
    .sort_values(ascending=False)
    .head(10)
)

# 4. Vehicle-trip feasibility
print("\n4. VEHICLE AND ROUTE ANALYSIS")

df["service_date"] = df["created_at"].dt.date

vehicle_groups = (
    df.groupby(
        ["service_date", "vehicle_number", "route"]
    )
    .agg(
        tickets=("passenger_count", "size"),
        passengers=("passenger_count", "sum"),
        first_ticket=("created_at", "min"),
        last_ticket=("created_at", "max")
    )
    .reset_index()
)

print("\nSample vehicle-route-day groups:")
print(vehicle_groups.head(10).to_string(index=False))

# 5. Stop analysis
print("\n5. STOP ANALYSIS")

print(
    "Unique boarding stops:",
    df["start_stop_name"].nunique()
)

print(
    "Unique destination stops:",
    df["end_stop_name"].nunique()
)

print("\nTop boarding stops:")
print(
    df["start_stop_name"]
    .value_counts()
    .head(10)
)

# 6. Passenger counts
print("\n6. PASSENGER COUNT DISTRIBUTION")

print(
    df["passenger_count"]
    .value_counts()
    .head(15)
)

# 7. Check hourly demand by day type
print("\n7. AVERAGE HOURLY DEMAND")

daily_hourly = (
    df.groupby(
        ["service_date", "hour"]
    )["passenger_count"]
    .sum()
    .reset_index()
)

daily_hourly["day_type"] = pd.to_datetime(
    daily_hourly["service_date"]
).dt.dayofweek.map(
    lambda x: "Weekend" if x >= 5 else "Weekday"
)

print(
    daily_hourly.groupby(
        ["day_type", "hour"]
    )["passenger_count"]
    .mean()
    .unstack(0)
    .round(1)
    .to_string()
)

# 8. Save route statistics
route_stats = (
    df.groupby("route")
    .agg(
        tickets=("passenger_count", "size"),
        passengers=("passenger_count", "sum"),
        vehicles=("vehicle_number", "nunique"),
        boarding_stops=("start_stop_name", "nunique")
    )
    .reset_index()
)

route_stats.to_csv(
    BASE / "outputs" / "route_statistics.csv",
    index=False
)

print("\nAudit completed successfully!")
