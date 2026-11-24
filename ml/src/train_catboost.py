
from pathlib import Path
import numpy as np
import pandas as pd
from catboost import CatBoostRegressor
import joblib

BASE = Path(__file__).resolve().parents[1]
OUT = BASE / "outputs"
MODELS = BASE / "models"

OUT.mkdir(parents=True, exist_ok=True)
MODELS.mkdir(parents=True, exist_ok=True)

print("Loading hourly demand data...")

df = pd.read_csv(
    OUT / "daily_hourly_demand.csv",
    parse_dates=["date"]
)

df["route"] = df["route"].astype(str)
df["is_weekend"] = (
    df["day_of_week"] >= 5
).astype(int)

features = [
    "route",
    "day_of_week",
    "hour",
    "is_weekend"
]

cutoff = pd.Timestamp("2026-10-25")

train = df[df["date"] < cutoff].copy()
test = df[df["date"] >= cutoff].copy()

X_train = train[features]
y_train = train["passengers"]

X_test = test[features]
y_test = test["passengers"]

print("Training rows:", len(train))
print("Testing rows:", len(test))

model = CatBoostRegressor(
    iterations=400,
    depth=6,
    learning_rate=0.05,
    loss_function="RMSE",
    cat_features=["route"],
    verbose=False,
    random_seed=42,
    thread_count=-1
)

print("Training CatBoost model...")

model.fit(X_train, y_train)

predictions = model.predict(X_test)

# Passenger demand cannot be negative
predictions = np.maximum(predictions, 0)

test["catboost_prediction"] = predictions

# Compare with the existing baseline
baseline = pd.read_csv(
    OUT / "hourly_demand_validation.csv",
    parse_dates=["date"]
)

baseline = baseline[
    ["route", "date", "hour", "prediction"]
].rename(
    columns={"prediction": "baseline_prediction"}
)

test = test.merge(
    baseline,
    on=["route", "date", "hour"],
    how="left",
    validate="one_to_one"
)

if test["baseline_prediction"].isna().any():
    raise ValueError(
        "Some baseline predictions are missing"
    )

def evaluate(actual, predicted):
    error = predicted - actual

    mae = np.mean(np.abs(error))
    rmse = np.sqrt(np.mean(error ** 2))

    wape = (
        np.abs(error).sum() / actual.sum() * 100
        if actual.sum() > 0 else np.nan
    )

    return mae, rmse, wape

print("\nMODEL COMPARISON")
print("=" * 60)

for name, column in [
    ("Historical baseline", "baseline_prediction"),
    ("CatBoost", "catboost_prediction")
]:
    mae, rmse, wape = evaluate(
        test["passengers"].to_numpy(),
        test[column].to_numpy()
    )

    print(
        f"{name}: "
        f"MAE={mae:.3f}, "
        f"RMSE={rmse:.3f}, "
        f"WAPE={wape:.2f}%"
    )

# Compare on the 20 busiest routes,
# selected from the training period only.
top_routes = (
    train.groupby("route")["passengers"]
    .sum()
    .nlargest(20)
    .index
)

top_test = test[
    test["route"].isin(top_routes)
]

print("\nTOP 20 TRAINING-DEMAND ROUTES")
print("=" * 60)

for name, column in [
    ("Historical baseline", "baseline_prediction"),
    ("CatBoost", "catboost_prediction")
]:
    mae, rmse, wape = evaluate(
        top_test["passengers"].to_numpy(),
        top_test[column].to_numpy()
    )

    print(
        f"{name}: "
        f"MAE={mae:.3f}, "
        f"RMSE={rmse:.3f}, "
        f"WAPE={wape:.2f}%"
    )

# Save outputs
model.save_model(
    str(MODELS / "catboost_hourly_demand.cbm")
)

test.to_csv(
    OUT / "catboost_validation.csv",
    index=False
)

print("\nSaved CatBoost model and predictions.")
