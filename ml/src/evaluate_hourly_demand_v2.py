
from pathlib import Path
import numpy as np
import pandas as pd

BASE = Path(__file__).resolve().parents[1]
OUT = BASE / "outputs"

df = pd.read_csv(
    OUT / "daily_hourly_demand_v2.csv",
    parse_dates=["date"]
)

df["day_of_week"] = df["day_of_week"].astype(int)
df["hour"] = df["hour"].astype(int)

train = df[df["date"] <= "2026-10-24"].copy()
test = df[df["date"] >= "2026-10-25"].copy()

keys = ["route", "day_of_week", "hour"]

# Model 1: original zero-filled historical average.
train_zero = train.copy()
train_zero["passengers"] = train_zero[
    "passengers"
].fillna(0)

zero_baseline = (
    train_zero.groupby(keys, as_index=False)
    .agg(pred_zero=("passengers", "mean"))
)

# Model 2: average on days with recorded ticket activity.
active_baseline = (
    train.groupby(keys, as_index=False)
    .agg(
        pred_active=("passengers", "mean"),
        active_days=("has_ticket_activity", "sum"),
        calendar_days=("date", "nunique")
    )
)

active_baseline["activity_coverage"] = (
    active_baseline["active_days"]
    / active_baseline["calendar_days"]
)

result = (
    test.merge(zero_baseline, on=keys, how="left")
    .merge(active_baseline, on=keys, how="left")
)

# Evaluate on observed test demand only.
observed = result[
    result["has_ticket_activity"]
].copy()

def metrics(data, prediction_col):
    valid = data.dropna(
        subset=["passengers", prediction_col]
    )

    if valid.empty:
        return None

    actual = valid["passengers"].to_numpy()
    predicted = valid[prediction_col].to_numpy()

    errors = np.abs(actual - predicted)

    return {
        "evaluated_rows": len(valid),
        "MAE": round(float(errors.mean()), 3),
        "RMSE": round(
            float(np.sqrt(np.mean((actual - predicted) ** 2))),
            3
        ),
        "WAPE_percent": round(
            float(errors.sum() / actual.sum() * 100),
            2
        ) if actual.sum() > 0 else None
    }

print("CHRONOLOGICAL DEMAND EVALUATION")
print("=" * 55)
print("Training:", "2026-10-01 to 2026-10-24")
print("Testing:", "2026-10-25 to 2026-10-31")
print("Total test route-hours:", len(result))
print("Observed test route-hours:", len(observed))

print("\nZERO-FILLED BASELINE")
print(metrics(observed, "pred_zero"))

print("\nACTIVITY-CONDITIONED BASELINE")
print(metrics(observed, "pred_active"))

# Fair comparison on exactly the same evaluable rows.
common = observed.dropna(
    subset=["pred_zero", "pred_active"]
)

print("\nCOMMON-ROW COMPARISON")
print("Common rows:", len(common))
print("Zero baseline:", metrics(common, "pred_zero"))
print("Active baseline:", metrics(common, "pred_active"))

coverage = (
    len(common) / len(observed)
    if len(observed) else 0
)

print(
    "\nActive-model coverage on observed test hours:",
    f"{coverage * 100:.2f}%"
)

result.to_csv(
    OUT / "hourly_demand_v2_evaluation.csv",
    index=False
)

print("\nSaved: outputs/hourly_demand_v2_evaluation.csv")
