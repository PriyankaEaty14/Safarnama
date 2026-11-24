
from pathlib import Path
import pandas as pd

BASE = Path(__file__).resolve().parents[1]
DATA = BASE / "data" / "processed"
OUT = BASE / "outputs"
OUT.mkdir(exist_ok=True)

v2 = pd.read_parquet(
    DATA / "validated_ticket_stops.parquet"
)

v3 = pd.read_parquet(
    DATA / "validated_ticket_stops_v3.parquet"
)

assert len(v2) == len(v3)

old_valid = v2["valid_order"].fillna(False).astype(bool)
new_valid = v3["valid_order"].fillna(False).astype(bool)

newly_valid = ~old_valid & new_valid

# Identify tickets with at least one newly matched stop.
new_start = (
    v2["start_stop_id"].isna()
    & v3["start_stop_id"].notna()
)

new_end = (
    v2["end_stop_id"].isna()
    & v3["end_stop_id"].notna()
)

recovered = v3.loc[
    newly_valid,
    [
        "route",
        "start_stop_name",
        "end_stop_name",
        "start_stop_id",
        "end_stop_id"
    ]
].copy()

recovered["new_boarding_match"] = (
    new_start.loc[newly_valid].to_numpy()
)

recovered["new_destination_match"] = (
    new_end.loc[newly_valid].to_numpy()
)

print("V3 RECOVERED MATCH AUDIT")
print("=" * 55)

print("Newly valid journeys:", len(recovered))
print(
    "New boarding matches:",
    int(recovered["new_boarding_match"].sum())
)
print(
    "New destination matches:",
    int(recovered["new_destination_match"].sum())
)
print(
    "Both stops newly matched:",
    int((
        recovered["new_boarding_match"]
        & recovered["new_destination_match"]
    ).sum())
)

print("\nTOP ROUTES WITH NEWLY VALID JOURNEYS")

print(
    recovered["route"]
    .value_counts()
    .head(20)
    .to_string()
)

# Save the full recovered-ticket audit.
recovered.to_csv(
    OUT / "v3_recovered_journeys.csv",
    index=False
)

# Reproducible sample for manual inspection.
sample = recovered.sample(
    n=min(100, len(recovered)),
    random_state=42
)

sample.to_csv(
    OUT / "v3_manual_review_sample.csv",
    index=False
)

print("\nSaved:")
print("outputs/v3_recovered_journeys.csv")
print("outputs/v3_manual_review_sample.csv")
print("\nAUDIT COMPLETE")
