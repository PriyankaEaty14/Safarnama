
from pathlib import Path
from demand_lookup import DemandLookup
import pandas as pd

BASE = Path(__file__).resolve().parents[1]

csv_path = (
    BASE / "outputs" / "demo_route_predictions.csv"
)

print("Loading actual demo predictions...")

df = pd.read_csv(csv_path)

print("Total records:", len(df))
print("Total routes:", df["route"].nunique())

assert len(df) == 3360, "Expected 3360 predictions"
assert df["route"].nunique() == 20, "Expected 20 routes"

lookup = DemandLookup(csv_path)

print("\nTEST 1: Existing route")

result = lookup.predict("717AUP", 4, 8)
print(result)

assert result["available"] is True
assert result["predicted_passengers"] >= 0

print("\nTEST 2: Missing route")

result = lookup.predict("INVALID_ROUTE", 4, 8)
print(result)

assert result["available"] is False
assert result["predicted_passengers"] is None

print("\nTEST 3: Compare lookup with original CSV")

sample = df[
    (df["route"] == "717AUP")
    & (df["day_of_week"] == 4)
    & (df["hour"] == 8)
]

assert len(sample) == 1

expected = float(sample.iloc[0]["predicted_passengers"])
actual = lookup.predict("717AUP", 4, 8)[
    "predicted_passengers"
]

assert abs(expected - actual) < 0.000001

print("CSV prediction:", expected)
print("Backend lookup:", actual)

print("\nALL REAL-DATA INTEGRATION TESTS PASSED!")
