
from pathlib import Path
import numpy as np
import pandas as pd

BASE = Path(__file__).resolve().parents[1]
OUT = BASE / "outputs"

print("Loading validation results...")

df = pd.read_csv(
    OUT / "hourly_demand_validation.csv"
)

df["absolute_error"] = (
    df["prediction"] - df["passengers"]
).abs()

# Route-level evaluation
summary = (
    df.groupby("route", as_index=False)
    .agg(
        actual_passengers=("passengers", "sum"),
        predicted_passengers=("prediction", "sum"),
        total_absolute_error=("absolute_error", "sum"),
        observations=("passengers", "size"),
        active_hours=("passengers", lambda x: (x > 0).sum())
    )
)

summary["MAE"] = (
    summary["total_absolute_error"]
    / summary["observations"]
)

summary["WAPE"] = np.where(
    summary["actual_passengers"] > 0,
    summary["total_absolute_error"]
    / summary["actual_passengers"] * 100,
    np.nan
)

# Highest-demand routes in the test period
top_routes = summary.sort_values(
    "actual_passengers",
    ascending=False
).head(20)

print("\nTOP 20 ROUTES BY OBSERVED DEMAND")
print("=" * 60)

print(
    top_routes[
        [
            "route",
            "actual_passengers",
            "predicted_passengers",
            "MAE",
            "WAPE",
            "active_hours"
        ]
    ].round(2).to_string(index=False)
)

# Weighted aggregate WAPE for top 20 routes
top_wape = (
    top_routes["total_absolute_error"].sum()
    / top_routes["actual_passengers"].sum()
    * 100
)

print("\nTop 20 route WAPE:", round(top_wape, 2), "%")

summary.to_csv(
    OUT / "route_validation_summary.csv",
    index=False
)

print("\nSaved route_validation_summary.csv")
