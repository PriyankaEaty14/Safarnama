
from pathlib import Path
import json
import pandas as pd

BASE = Path(__file__).resolve().parents[1]
DATA = BASE / "data" / "processed"
OUT = BASE / "outputs"
OUT.mkdir(parents=True, exist_ok=True)

path = DATA / "validated_ticket_stops.parquet"

print("Loading validated ticket records...")
df = pd.read_parquet(path)

required = [
    "route",
    "start_stop_id",
    "end_stop_id",
    "valid_order"
]

missing = [c for c in required if c not in df.columns]
if missing:
    raise ValueError(f"Missing columns: {missing}")

start = df["start_stop_id"].notna()
end = df["end_stop_id"].notna()
valid = df["valid_order"].fillna(False).astype(bool)

same_stop = (
    start & end &
    (df["start_stop_id"].astype(str)
     == df["end_stop_id"].astype(str))
)

# Assign exactly one category per record.
category = pd.Series(
    "invalid_order_or_pattern",
    index=df.index,
    dtype="object"
)

category.loc[~start & ~end] = "both_stops_unmatched"
category.loc[~start & end] = "boarding_unmatched"
category.loc[start & ~end] = "destination_unmatched"
category.loc[same_stop] = "same_stop"
category.loc[valid] = "valid_order"

# Detect inconsistencies in the existing validation.
inconsistent = valid & (~start | ~end | same_stop)
if inconsistent.any():
    raise ValueError(
        f"{inconsistent.sum()} inconsistent valid_order records"
    )

counts = category.value_counts()

total = len(df)
valid_count = int(valid.sum())
excluded = total - valid_count

print("\nTICKET EXCLUSION AUDIT")
print("=" * 55)
print("Total cleaned tickets:", total)
print("Valid ordered journeys:", valid_count)
print("Not validated:", excluded)

print("\nBREAKDOWN")
print("-" * 55)

results = []

for name in [
    "valid_order",
    "both_stops_unmatched",
    "boarding_unmatched",
    "destination_unmatched",
    "same_stop",
    "invalid_order_or_pattern"
]:
    count = int(counts.get(name, 0))
    pct = 100 * count / total if total else 0

    print(f"{name:30s} {count:10,d}  {pct:6.2f}%")

    results.append({
        "category": name,
        "tickets": count,
        "percentage": round(pct, 2)
    })

assert sum(x["tickets"] for x in results) == total

summary = {
    "total_tickets": total,
    "valid_order_tickets": valid_count,
    "not_validated_tickets": excluded,
    "valid_percentage": round(
        100 * valid_count / total, 2
    ) if total else 0,
    "categories": results,
    "note": (
        "Failure categories describe matching and GTFS "
        "validation outcomes, not necessarily bad tickets."
    )
}

json_path = OUT / "ticket_exclusion_audit.json"
csv_path = OUT / "ticket_exclusion_audit.csv"

json_path.write_text(
    json.dumps(summary, indent=2),
    encoding="utf-8"
)

pd.DataFrame(results).to_csv(
    csv_path,
    index=False
)

print("\nSaved:", json_path)
print("Saved:", csv_path)
print("\nAUDIT COMPLETED SUCCESSFULLY")
