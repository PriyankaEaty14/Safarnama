
from pathlib import Path
from collections import defaultdict
import re
import pandas as pd

BASE = Path(__file__).resolve().parents[1]
DATA = BASE / "data" / "processed"
OUT = BASE / "outputs"

def normalize(value):
    if pd.isna(value):
        return ""
    value = str(value).upper()
    value = re.sub(r"[^A-Z0-9]+", " ", value)
    return re.sub(r"\s+", " ", value).strip()

print("Loading V2 and GTFS data...")

mapping = pd.read_csv(
    OUT / "stop_matching_report_v2.csv",
    dtype={"route": str, "ticket_stop_name": str,
           "stop_id": str}
)

route_stops = pd.read_parquet(
    DATA / "route_stops.parquet"
)

tickets = pd.read_parquet(
    DATA / "cleaned_tickets.parquet",
    columns=["route", "start_stop_name", "end_stop_name"]
)

# Build route-specific component lookup.
components = defaultdict(set)

for row in route_stops.itertuples(index=False):
    for part in str(row.stop_name).split("/"):
        key = normalize(part)
        if key:
            components[(str(row.route), key)].add(
                str(row.stop_id)
            )

mapping["v3_stop_id"] = mapping["stop_id"]
mapping["v3_method"] = mapping["method"]

recovered_names = 0

for idx, row in mapping[mapping["stop_id"].isna()].iterrows():
    key = (str(row["route"]), normalize(row["ticket_stop_name"]))
    candidates = components.get(key, set())

    if len(candidates) == 1:
        mapping.at[idx, "v3_stop_id"] = next(iter(candidates))
        mapping.at[idx, "v3_method"] = "component_exact"
        recovered_names += 1

print("Recovered route-stop names:", recovered_names)

# Retain only mapping fields needed for merging.
v3_map = mapping[
    ["route", "ticket_stop_name", "v3_stop_id", "v3_method"]
].copy()

start_map = v3_map.rename(columns={
    "ticket_stop_name": "start_stop_name",
    "v3_stop_id": "start_stop_id",
    "v3_method": "start_method"
})

end_map = v3_map.rename(columns={
    "ticket_stop_name": "end_stop_name",
    "v3_stop_id": "end_stop_id",
    "v3_method": "end_method"
})

tickets = tickets.merge(
    start_map,
    on=["route", "start_stop_name"],
    how="left",
    validate="many_to_one"
)

tickets = tickets.merge(
    end_map,
    on=["route", "end_stop_name"],
    how="left",
    validate="many_to_one"
)

both = (
    tickets["start_stop_id"].notna()
    & tickets["end_stop_id"].notna()
)

print("\nV3 MATCHING RESULTS")
print("=" * 45)
print("Total tickets:", len(tickets))
print("Boarding matched:",
      f"{tickets['start_stop_id'].notna().mean():.2%}")
print("Destination matched:",
      f"{tickets['end_stop_id'].notna().mean():.2%}")
print("Both matched:", f"{both.mean():.2%}")

mapping.to_csv(
    OUT / "stop_matching_report_v3.csv",
    index=False
)

tickets.to_parquet(
    DATA / "matched_ticket_stops_v3.parquet",
    index=False
)

print("\nSaved V3 outputs.")
print("Original V2 outputs remain unchanged.")
