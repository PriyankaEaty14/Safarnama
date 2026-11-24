
from pathlib import Path
import pandas as pd

BASE = Path(__file__).resolve().parents[1]
OUT = BASE / "outputs"
OUT.mkdir(parents=True, exist_ok=True)

print("Preparing backend handoff...")

baseline = pd.read_csv(
    OUT / "hourly_demand_baseline.csv"
)

# Select busiest routes using observed demand
daily = pd.read_csv(
    OUT / "daily_hourly_demand.csv"
)

top_routes = (
    daily.groupby("route")["passengers"]
    .sum()
    .nlargest(20)
    .index
)

demo = baseline[
    baseline["route"].isin(top_routes)
].copy()

demo = demo.sort_values(
    ["route", "day_of_week", "hour"]
)

path = OUT / "demo_route_predictions.csv"

demo.to_csv(path, index=False)

print("\nBACKEND HANDOFF COMPLETE")
print("=" * 45)
print("Demo routes:", demo["route"].nunique())
print("Prediction rows:", len(demo))
print("Saved:", path)

print("\nSelected routes:")
print(", ".join(top_routes))
