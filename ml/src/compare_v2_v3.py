
from pathlib import Path
import pandas as pd

BASE = Path(__file__).resolve().parents[1]
DATA = BASE / "data" / "processed"

v2 = pd.read_parquet(
    DATA / "validated_ticket_stops.parquet",
    columns=[
        "start_stop_id",
        "end_stop_id",
        "valid_order"
    ]
)

v3 = pd.read_parquet(
    DATA / "validated_ticket_stops_v3.parquet",
    columns=[
        "start_stop_id",
        "end_stop_id",
        "valid_order"
    ]
)

assert len(v2) == len(v3), "Dataset row counts differ"

# Both pipelines originate from cleaned_tickets.parquet
# and preserve its row order.
old_valid = v2["valid_order"].fillna(False).astype(bool)
new_valid = v3["valid_order"].fillna(False).astype(bool)

lost = old_valid & ~new_valid
gained = ~old_valid & new_valid

def changed_existing_ids(column):
    old = v2[column].astype("string")
    new = v3[column].astype("string")

    return int(
        (old.notna() & old.ne(new).fillna(True)).sum()
    )

start_changes = changed_existing_ids("start_stop_id")
end_changes = changed_existing_ids("end_stop_id")

print("V2 vs V3 REGRESSION CHECK")
print("=" * 50)
print("Total tickets:", len(v2))
print("V2 valid journeys:", int(old_valid.sum()))
print("V3 valid journeys:", int(new_valid.sum()))
print("Newly valid journeys:", int(gained.sum()))
print("Previously valid journeys lost:", int(lost.sum()))
print("Existing boarding IDs changed:", start_changes)
print("Existing destination IDs changed:", end_changes)

assert lost.sum() == 0, "Some V2-valid journeys were lost"
assert start_changes == 0, "Existing boarding IDs changed"
assert end_changes == 0, "Existing destination IDs changed"

print("\nV3 REGRESSION CHECK PASSED!")
