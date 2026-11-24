
from pathlib import Path
from collections import defaultdict
import re

import pandas as pd
from rapidfuzz import fuzz, process

BASE = Path(__file__).resolve().parents[1]
DATA = BASE / "data" / "processed"
OUT = BASE / "outputs"
OUT.mkdir(parents=True, exist_ok=True)

print("Loading datasets...")

tickets = pd.read_parquet(
    DATA / "cleaned_tickets.parquet",
    columns=[
        "route",
        "start_stop_name",
        "end_stop_name"
    ]
)

route_stops = pd.read_parquet(
    DATA / "route_stops.parquet"
)

# Normalize stop names
def normalize(value):
    if pd.isna(value):
        return ""

    value = str(value).upper().strip()
    value = re.sub(r"[^A-Z0-9]+", " ", value)
    value = re.sub(r"\s+", " ", value)

    return value.strip()

route_stops["normalized"] = (
    route_stops["stop_name"].map(normalize)
)

# Build lookup for each route
lookup = defaultdict(lambda: defaultdict(set))

for row in route_stops.itertuples(index=False):
    lookup[row.route][row.normalized].add(row.stop_id)

# Match a stop only against stops on its route
def match_stop(route, stop_name):
    normalized = normalize(stop_name)

    if not normalized or route not in lookup:
        return None, "unmatched", 0

    candidates = lookup[route]

    # Exact normalized match
    if normalized in candidates:
        ids = candidates[normalized]

        if len(ids) == 1:
            return next(iter(ids)), "exact", 100

        return None, "ambiguous", 100

    # Conservative fuzzy matching
    result = process.extractOne(
        normalized,
        candidates.keys(),
        scorer=fuzz.ratio,
        score_cutoff=92
    )

    if result is None:
        return None, "unmatched", 0

    matched_name, score, _ = result
    ids = candidates[matched_name]

    if len(ids) != 1:
        return None, "ambiguous", score

    return next(iter(ids)), "fuzzy", score

# Avoid repeating matching for identical names
pairs = set()

for row in tickets.itertuples(index=False):
    pairs.add((row.route, row.start_stop_name))
    pairs.add((row.route, row.end_stop_name))

print("Unique route-stop names to match:", len(pairs))

mapping = []

for route, name in sorted(pairs):
    stop_id, method, score = match_stop(route, name)

    mapping.append({
        "route": route,
        "ticket_stop_name": name,
        "stop_id": stop_id,
        "method": method,
        "score": score
    })

mapping_df = pd.DataFrame(mapping)

mapping_df.to_csv(
    OUT / "stop_matching_report_v2.csv",
    index=False
)

# Attach boarding stop IDs
start_map = mapping_df.rename(
    columns={
        "ticket_stop_name": "start_stop_name",
        "stop_id": "start_stop_id",
        "method": "start_method",
        "score": "start_score"
    }
)

# Attach destination stop IDs
end_map = mapping_df.rename(
    columns={
        "ticket_stop_name": "end_stop_name",
        "stop_id": "end_stop_id",
        "method": "end_method",
        "score": "end_score"
    }
)

tickets = tickets.merge(
    start_map,
    on=["route", "start_stop_name"],
    how="left"
)

tickets = tickets.merge(
    end_map,
    on=["route", "end_stop_name"],
    how="left"
)

both = (
    tickets["start_stop_id"].notna()
    & tickets["end_stop_id"].notna()
)

print("\nMATCHING RESULTS V2")
print("=" * 45)

print("Total tickets:", len(tickets))

print(
    "Boarding matched:",
    f"{tickets['start_stop_id'].notna().mean():.2%}"
)

print(
    "Destination matched:",
    f"{tickets['end_stop_id'].notna().mean():.2%}"
)

print(
    "Both matched:",
    f"{both.mean():.2%}"
)

print("\nBoarding match methods:")
print(tickets["start_method"].value_counts())

print("\nDestination match methods:")
print(tickets["end_method"].value_counts())

tickets.to_parquet(
    DATA / "matched_ticket_stops_v2.parquet",
    index=False
)

print("\nSaved matching report and matched tickets.")
