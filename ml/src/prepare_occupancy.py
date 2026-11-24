
from pathlib import Path
import pandas as pd

BASE = Path(__file__).resolve().parents[1]
DATA = BASE / "data" / "processed"

print("Loading cleaned tickets...")

original = pd.read_parquet(
    DATA / "cleaned_tickets.parquet"
)

print("Loading validated stop matches...")

matched = pd.read_parquet(
    DATA / "validated_ticket_stops.parquet"
)

# The matching pipeline preserved row order,
# but verify this assumption before combining.
if len(original) != len(matched):
    raise ValueError("Dataset row counts do not match!")

for col in ["route", "start_stop_name", "end_stop_name"]:
    same = (
        original[col].astype("string").fillna("")
        == matched[col].astype("string").fillna("")
    ).all()

    if not same:
        raise ValueError(
            f"Row alignment failed for column: {col}"
        )

print("Row alignment verified.")

# Attach stop matching information
columns = [
    "start_stop_id",
    "end_stop_id",
    "start_method",
    "end_method",
    "valid_order"
]

for col in columns:
    original[col] = matched[col].to_numpy()

# Keep only candidate valid journeys
valid = original[
    original["valid_order"] == True
].copy()

valid["service_date"] = valid["created_at"].dt.date
valid["ticket_hour"] = valid["created_at"].dt.hour

valid = valid.sort_values(
    [
        "service_date",
        "vehicle_number",
        "route",
        "created_at"
    ]
)

output = DATA / "occupancy_ready_tickets.parquet"

valid.to_parquet(output, index=False)

print("\nOCCUPANCY DATA PREPARATION")
print("=" * 45)

print("Original tickets:", len(original))
print("Candidate valid journeys:", len(valid))

print(
    "Unique vehicles:",
    valid["vehicle_number"].nunique()
)

print(
    "Unique routes:",
    valid["route"].nunique()
)

print("\nFirst five records:")
print(
    valid[
        [
            "vehicle_number",
            "route",
            "created_at",
            "start_stop_id",
            "end_stop_id",
            "passenger_count"
        ]
    ].head().to_string(index=False)
)

print("\nSaved:", output)
