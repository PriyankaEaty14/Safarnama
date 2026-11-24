
from pathlib import Path
from collections import defaultdict
import re
import pandas as pd

BASE = Path(__file__).resolve().parents[1]
DATA = BASE / "data" / "processed"
OUT = BASE / "outputs"

route_stops = pd.read_parquet(DATA / "route_stops.parquet")
failures = pd.read_csv(
    OUT / "unmatched_stop_diagnosis.csv",
    dtype={"route": str, "ticket_stop_name": str}
)

def normalize(value):
    if pd.isna(value):
        return ""
    value = str(value).upper()
    value = re.sub(r"[^A-Z0-9]+", " ", value)
    return re.sub(r"\s+", " ", value).strip()

# Map route + individual GTFS name component to stop IDs.
component_lookup = defaultdict(set)

for row in route_stops.itertuples(index=False):
    route = str(row.route)
    stop_id = str(row.stop_id)

    for part in str(row.stop_name).split("/"):
        key = normalize(part)
        if key:
            component_lookup[(route, key)].add(stop_id)

results = []

for row in failures.itertuples(index=False):
    route = str(row.route)
    name = normalize(row.ticket_stop_name)

    ids = component_lookup.get((route, name), set())

    if len(ids) == 1:
        status = "unique_component_match"
        candidate_id = next(iter(ids))
    elif len(ids) > 1:
        status = "ambiguous_component_match"
        candidate_id = None
    else:
        status = "no_component_match"
        candidate_id = None

    results.append({
        "route": route,
        "ticket_stop_name": row.ticket_stop_name,
        "ticket_occurrences": int(row.ticket_occurrences),
        "status": status,
        "candidate_stop_id": candidate_id,
        "candidate_count": len(ids)
    })

result = pd.DataFrame(results)

print("COMPONENT MATCHING DIAGNOSTIC")
print("=" * 60)

summary = result.groupby("status").agg(
    unique_route_stop_names=("route", "size"),
    ticket_occurrences=("ticket_occurrences", "sum")
)

print(summary.to_string())

print("\nTOP POTENTIALLY RECOVERABLE NAMES")
print("=" * 60)

recoverable = result[
    result["status"] == "unique_component_match"
].sort_values("ticket_occurrences", ascending=False)

print(
    recoverable[
        ["route", "ticket_stop_name",
         "candidate_stop_id", "ticket_occurrences"]
    ].head(20).to_string(index=False)
)

result.to_csv(
    OUT / "component_matching_diagnostic.csv",
    index=False
)

print("\nSaved: outputs/component_matching_diagnostic.csv")
print("No existing matches were modified.")
