
from pathlib import Path
import pandas as pd

BASE = Path(__file__).resolve().parents[1]
DATA = BASE / "data" / "processed"
OUT = BASE / "outputs"

OUT.mkdir(parents=True, exist_ok=True)

print("Loading cleaned ticket records...")

df = pd.read_parquet(
    DATA / "cleaned_tickets.parquet",
    columns=[
        "route",
        "created_at",
        "passenger_count"
    ]
)

df["date"] = df["created_at"].dt.date
df["day_of_week"] = df["created_at"].dt.day_of_week
df["hour"] = df["created_at"].dt.hour

# Count passenger demand for each route,
# date and hour.
daily_hourly = (
    df.groupby(
        ["route", "date", "day_of_week", "hour"],
        as_index=False
    )
    .agg(
        passengers=("passenger_count", "sum"),
        ticket_records=("passenger_count", "size")
    )
)

# Build a calendar of all observed dates,
# routes and hours, including zero-demand slots.
dates = pd.DataFrame({
    "date": sorted(df["date"].unique())
})

dates["day_of_week"] = pd.to_datetime(
    dates["date"]
).dt.day_of_week

routes = pd.DataFrame({
    "route": sorted(df["route"].unique())
})

hours = pd.DataFrame({
    "hour": range(24)
})

calendar = (
    routes.merge(dates, how="cross")
    .merge(hours, how="cross")
)

daily_hourly = calendar.merge(
    daily_hourly,
    on=["route", "date", "day_of_week", "hour"],
    how="left"
)

daily_hourly[
    ["passengers", "ticket_records"]
] = daily_hourly[
    ["passengers", "ticket_records"]
].fillna(0)

# Historical average for each route,
# weekday and hour.
baseline = (
    daily_hourly.groupby(
        ["route", "day_of_week", "hour"],
        as_index=False
    )
    .agg(
        predicted_passengers=(
            "passengers", "mean"
        ),
        daily_std=(
            "passengers", "std"
        ),
        observed_days=(
            "date", "nunique"
        )
    )
)

baseline["daily_std"] = (
    baseline["daily_std"].fillna(0)
)

baseline["predicted_passengers"] = (
    baseline["predicted_passengers"].round(2)
)

baseline["daily_std"] = (
    baseline["daily_std"].round(2)
)

daily_hourly.to_csv(
    OUT / "daily_hourly_demand.csv",
    index=False
)

baseline.to_csv(
    OUT / "hourly_demand_baseline.csv",
    index=False
)

print("\nHOURLY DEMAND BASELINE COMPLETE")
print("=" * 45)

print("Routes:", df["route"].nunique())
print("Dates:", df["date"].nunique())
print("Baseline rows:", len(baseline))

print("\nSample predictions for route 717AUP:")
print(
    baseline[
        (baseline["route"] == "717AUP")
        & (baseline["day_of_week"] == 4)
        & (baseline["hour"].between(7, 10))
    ].to_string(index=False)
)

print("\nSaved:")
print(OUT / "daily_hourly_demand.csv")
print(OUT / "hourly_demand_baseline.csv")
