
from pathlib import Path
import numpy as np
import pandas as pd

BASE = Path(__file__).resolve().parents[1]
OUT = BASE / "outputs"

df = pd.read_csv(
    OUT / "daily_hourly_demand_v2.csv",
    parse_dates=["date"]
)

train = df[df["date"] <= "2026-10-24"].copy()
test = df[df["date"] >= "2026-10-25"].copy()

keys = ["route", "day_of_week", "hour"]

# Original historical baseline.
train_zero = train.copy()
train_zero["passengers"] = (
    train_zero["passengers"].fillna(0)
)

zero_model = (
    train_zero.groupby(keys, as_index=False)
    .agg(pred_zero=("passengers", "mean"))
)

# Activity-conditioned baseline.
active_model = (
    train.groupby(keys, as_index=False)
    .agg(
        pred_active=("passengers", "mean"),
        active_days=("has_ticket_activity", "sum")
    )
)

result = (
    test.merge(zero_model, on=keys, how="left")
    .merge(active_model, on=keys, how="left")
)

# Use activity-conditioned demand only when
# at least three training dates have transactions.
use_active = (
    (result["active_days"] >= 3)
    & result["pred_active"].notna()
)

result["pred_hybrid"] = np.where(
    use_active,
    result["pred_active"],
    result["pred_zero"]
)

result["prediction_source"] = np.where(
    use_active,
    "activity_conditioned",
    "zero_filled_fallback"
)

# Evaluate on test hours with recorded transactions.
observed = result[
    result["has_ticket_activity"]
].copy()

def evaluate(data, prediction_col):
    valid = data.dropna(
        subset=["passengers", prediction_col]
    )

    actual = valid["passengers"].to_numpy()
    pred = valid[prediction_col].to_numpy()

    error = np.abs(actual - pred)

    return {
        "rows": len(valid),
        "MAE": round(float(error.mean()), 3),
        "RMSE": round(
            float(np.sqrt(np.mean((actual - pred) ** 2))),
            3
        ),
        "WAPE_percent": round(
            float(error.sum() / actual.sum() * 100),
            2
        )
    }

print("HYBRID DEMAND EVALUATION")
print("=" * 55)
print("Observed test route-hours:", len(observed))

print("\nORIGINAL BASELINE")
print(evaluate(observed, "pred_zero"))

print("\nHYBRID BASELINE")
print(evaluate(observed, "pred_hybrid"))

print("\nPREDICTION SOURCES")
print(
    observed["prediction_source"]
    .value_counts()
    .to_string()
)

print(
    "\nMissing hybrid predictions:",
    int(observed["pred_hybrid"].isna().sum())
)

result.to_csv(
    OUT / "hybrid_demand_evaluation.csv",
    index=False
)

print("\nSaved: outputs/hybrid_demand_evaluation.csv")
