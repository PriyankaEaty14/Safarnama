
from pathlib import Path
from rapidfuzz import fuzz, process
import pandas as pd
import re

BASE = Path(__file__).resolve().parents[1]
DATA = BASE / "data" / "processed"
OUT = BASE / "outputs"

route_stops = pd.read_parquet(
    DATA / "route_stops.parquet"
)

failures = pd.read_csv(
    OUT / "unmatched_stop_diagnosis.csv"
)

def normalize(value):
    if pd.isna(value):
        return ""
    value = str(value).upper()
    value = re.sub(r"[^A-Z0-9]+", " ", value)
    return re.sub(r"\s+", " ", value).strip()

route_stops["normalized"] = (
    route_stops["stop_name"].map(normalize)
)

# Examine the 30 highest-impact unmatched names.
top = failures.sort_values(
    "ticket_occurrences",
    ascending=False
).head(30)

results = []

for row in top.itertuples(index=False):
    candidates = route_stops[
        route_stops["route"] == row.route
    ]

    names = candidates["normalized"].dropna().unique().tolist()

    matches = process.extract(
        normalize(row.ticket_stop_name),
        names,
        scorer=fuzz.WRatio,
        limit=3
    ) if names else []

    for rank, (matched, score, _) in enumerate(matches, 1):
        matching_rows = candidates[
            candidates["normalized"] == matched
        ]

        results.append({
            "route": row.route,
            "ticket_stop_name": row.ticket_stop_name,
            "ticket_occurrences": row.ticket_occurrences,
            "candidate_rank": rank,
            "gtfs_stop_names": " | ".join(
                sorted(matching_rows["stop_name"].astype(str).unique())
            ),
            "gtfs_stop_ids": " | ".join(
                sorted(matching_rows["stop_id"].astype(str).unique())
            ),
            "similarity_score": round(score, 2)
        })

result = pd.DataFrame(results)

path = OUT / "stop_candidate_review.csv"
result.to_csv(path, index=False)

print("TOP GTFS CANDIDATES")
print("=" * 75)

if result.empty:
    print("No route-specific candidates found.")
else:
    print(
        result[
            [
                "route",
                "ticket_stop_name",
                "candidate_rank",
                "gtfs_stop_names",
                "similarity_score"
            ]
        ].head(30).to_string(index=False)
    )

print("\nSaved:", path)
