
from pathlib import Path
import pandas as pd

BASE = Path(__file__).resolve().parents[1]
DATA = BASE / "data" / "processed"
OUT = BASE / "outputs"
OUT.mkdir(parents=True, exist_ok=True)

print("Loading cleaned ticket records...")

df = pd.read_parquet(
    DATA / "cleaned_tickets.parquet",
    columns=["route", "created_at", "passenger_count"]
)

df["created_at"] = pd.to_datetime(
    df["created_at"], errors="coerce"
)

df = df.dropna(
    subset=["route", "created_at", "passenger_count"]
).copy()

df["date"] = df["created_at"].dt.date
df["day_of_week"] = df["created_at"].dt.dayofweek
df["hour"] = df["created_at"].dt.hour

# Aggregate only route-hours containing transactions.
observed = (
    df.groupby(
        ["route", "date", "day_of_week", "hour"],
        as_index=False
    )
    .agg(
        passengers=("passenger_count", "sum"),
        ticket_records=("passenger_count", "size")
    )
)

observed["has_ticket_activity"] = True

# Create a complete comparison calendar.
dates = pd.DataFrame({
    "date": sorted(df["date"].unique())
})

dates["day_of_week"] = pd.to_datetime(
    dates["date"]
).dt.dayofweek

routes = pd.DataFrame({
    "route": sorted(df["route"].unique())
})

hours = pd.DataFrame({"hour": range(24)})

calendar = (
    routes.merge(dates, how="cross")
    .merge(hours, how="cross")
)

daily = calendar.merge(
    observed,
    on=["route", "date", "day_of_week", "hour"],
    how="left",
    validate="one_to_one"
)

daily["has_ticket_activity"] = (
    daily["has_ticket_activity"].fillna(False).astype(bool)
)

# Preserve missing demand as NaN.
# A missing transaction does not prove zero passengers.
daily["data_status"] = daily[
    "has_ticket_activity"
].map({
    True: "ticket_activity_observed",
    False: "no_ticket_activity_recorded"
})

baseline = (
    daily.groupby(
        ["route", "day_of_week", "hour"],
        as_index=False
    )
    .agg(
        predicted_passengers_active=(
            "passengers", "mean"
        ),
        active_day_std=("passengers", "std"),
        active_days=("has_ticket_activity", "sum"),
        calendar_days=("date", "nunique")
    )
)

baseline["activity_coverage"] = (
    baseline["active_days"] /
    baseline["calendar_days"]
)

baseline["active_day_std"] = (
    baseline["active_day_std"].fillna(0)
)

# Predictions remain missing when there are no
# recorded transactions for that weekday-hour.
baseline["predicted_passengers_active"] = (
    baseline["predicted_passengers_active"].round(2)
)

baseline["active_day_std"] = (
    baseline["active_day_std"].round(2)
)

baseline["activity_coverage"] = (
    baseline["activity_coverage"].round(4)
)

daily_path = OUT / "daily_hourly_demand_v2.csv"
baseline_path = OUT / "hourly_demand_baseline_v2.csv"

daily.to_csv(daily_path, index=False)
baseline.to_csv(baseline_path, index=False)

print("\nDEMAND DATA V2 COMPLETE")
print("=" * 50)
print("Routes:", df["route"].nunique())
print("Dates:", df["date"].nunique())
print("Calendar route-hours:", len(daily))
print(
    "Route-hours with ticket activity:",
    int(daily["has_ticket_activity"].sum())
)
print(
    "Route-hours without recorded activity:",
    int((~daily["has_ticket_activity"]).sum())
)

print("\nSample for route 717AUP:")
print(
    baseline[
        (baseline["route"] == "717AUP")
        & (baseline["day_of_week"] == 4)
        & (baseline["hour"].between(7, 10))
    ].to_string(index=False)
)

print("\nSaved:")
print(daily_path)
print(baseline_path)
