
from pathlib import Path
import json
import pandas as pd

BASE = Path(__file__).resolve().parents[1]
OUT = BASE / "outputs"
OUT.mkdir(parents=True, exist_ok=True)

print("Loading selected historical baseline...")

df = pd.read_csv(
    OUT / "hourly_demand_baseline.csv"
)

# Clean and validate exported values
required = [
    "route",
    "day_of_week",
    "hour",
    "predicted_passengers",
    "daily_std",
    "observed_days"
]

if df[required].isna().any().any():
    raise ValueError(
        "Baseline contains missing required values"
    )

records = []

for row in df.itertuples(index=False):
    records.append({
        "route": str(row.route),
        "day_of_week": int(row.day_of_week),
        "hour": int(row.hour),
        "predicted_passengers": float(
            row.predicted_passengers
        ),
        "daily_std": float(row.daily_std),
        "observed_days": int(row.observed_days)
    })

payload = {
    "model_name": "historical_hourly_baseline",
    "model_version": "1.0",
    "training_period": {
        "start": "2026-10-01",
        "end": "2026-10-31"
    },
    "timezone": "Asia/Kolkata",
    "metric": "expected_ticketed_passengers_per_route_hour",
    "is_live_prediction": False,
    "is_bus_occupancy": False,
    "predictions": records
}

path = OUT / "hourly_demand_predictions.json"

with open(path, "w", encoding="utf-8") as f:
    json.dump(payload, f, separators=(",", ":"))

print("\nPREDICTION EXPORT COMPLETE")
print("=" * 45)
print("Total prediction records:", len(records))
print("Saved:", path)

print("\nSample prediction:")
print(json.dumps(records[0], indent=2))
