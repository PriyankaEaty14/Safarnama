
from pathlib import Path
import pandas as pd

BASE = Path(__file__).resolve().parents[1]
DATA = BASE / "data" / "processed"
OUT = BASE / "outputs"

mapping = pd.read_csv(
    OUT / "stop_matching_report_v3.csv",
    dtype={
        "route": str,
        "v3_stop_id": str
    }
)

route_stops = pd.read_parquet(
    DATA / "route_stops.parquet"
)

route_stops["route"] = route_stops["route"].astype(str)
route_stops["stop_id"] = route_stops["stop_id"].astype(str)

reference = (
    route_stops[["route", "stop_id"]]
    .drop_duplicates()
    .rename(columns={"stop_id": "v3_stop_id"})
)

recovered = mapping[
    mapping["v3_method"] == "component_exact"
].copy()

checked = recovered.merge(
    reference.assign(exists_in_gtfs=True),
    on=["route", "v3_stop_id"],
    how="left",
    validate="many_to_one"
)

missing = checked["exists_in_gtfs"].isna()

print("V3 MAPPING INTEGRITY CHECK")
print("=" * 50)
print("Recovered mappings:", len(recovered))
print("Valid route-stop references:", int((~missing).sum()))
print("Missing route-stop references:", int(missing.sum()))

assert missing.sum() == 0, (
    "Some recovered stop IDs are absent from route_stops"
)

print("\nV3 MAPPING INTEGRITY CHECK PASSED!")
