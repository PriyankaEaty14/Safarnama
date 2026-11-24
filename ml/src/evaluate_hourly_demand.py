
from pathlib import Path
import numpy as np
import pandas as pd

BASE = Path(__file__).resolve().parents[1]
OUT = BASE / "outputs"

print("Loading hourly passenger demand...")

df = pd.read_csv(
    OUT / "daily_hourly_demand.csv",
    parse_dates=["date"]
)

# Chronological train/test split
cutoff = pd.Timestamp("2026-10-25")

train = df[df["date"] < cutoff].copy()
test = df[df["date"] >= cutoff].copy()

print("Training days:", train["date"].nunique())
print("Testing days:", test["date"].nunique())

# Learn average hourly demand using training data only
baseline = (
    train.groupby(
        ["route", "day_of_week", "hour"],
        as_index=False
    )
    .agg(
        prediction=("passengers", "mean")
    )
)

# Fallback for route/hour combinations without
# a matching weekday in training
route_hour = (
    train.groupby(["route", "hour"], as_index=False)
    .agg(route_hour_mean=("passengers", "mean"))
)

# Predict unseen test dates
test = test.merge(
    baseline,
    on=["route", "day_of_week", "hour"],
    how="left"
)

test = test.merge(
    route_hour,
    on=["route", "hour"],
    how="left"
)

test["prediction"] = (
    test["prediction"]
    .fillna(test["route_hour_mean"])
    .fillna(0)
)

actual = test["passengers"].to_numpy()
predicted = test["prediction"].to_numpy()

errors = predicted - actual

mae = np.mean(np.abs(errors))
rmse = np.sqrt(np.mean(errors ** 2))

total_actual = actual.sum()

wape = (
    np.abs(errors).sum() / total_actual * 100
    if total_actual > 0 else np.nan
)

bias = np.mean(errors)

# Additional evaluation on active route-hours
active = test[test["passengers"] > 0].copy()

active_mae = (
    np.mean(
        np.abs(
            active["prediction"] - active["passengers"]
        )
    )
    if len(active) > 0 else np.nan
)

print("\nHOURLY DEMAND VALIDATION RESULTS")
print("=" * 50)

print("Test observations:", len(test))
print("MAE:", round(mae, 3))
print("RMSE:", round(rmse, 3))
print("WAPE:", round(wape, 2), "%")
print("Bias:", round(bias, 3))
print("MAE on active route-hours:",
      round(active_mae, 3))

# Save predictions for further analysis
test["absolute_error"] = np.abs(
    test["prediction"] - test["passengers"]
)

test.to_csv(
    OUT / "hourly_demand_validation.csv",
    index=False
)

print("\nRoute 717AUP validation sample:")

sample = test[
    (test["route"] == "717AUP")
    & (test["hour"].between(7, 10))
].sort_values(["date", "hour"])

print(
    sample[
        [
            "date",
            "hour",
            "passengers",
            "prediction",
            "absolute_error"
        ]
    ].head(16).to_string(index=False)
)

print("\nSaved hourly_demand_validation.csv")
