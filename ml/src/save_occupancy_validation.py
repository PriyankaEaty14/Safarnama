
from pathlib import Path
import json
import pandas as pd

BASE = Path(__file__).resolve().parents[1]
OUT = BASE / "outputs"

df = pd.read_csv(
    OUT / "audited_candidate_occupancy_profile.csv"
)

report = json.loads(
    (OUT / "audited_candidate_run_report.json").read_text(
        encoding="utf-8"
    )
)

boardings = int(df["boardings"].sum())
alightings = int(df["alightings"].sum())
calculated_load = (
    df["boardings"] - df["alightings"]
).cumsum()

assert (calculated_load == df["ticket_observed_load"]).all()
assert (calculated_load >= 0).all()
assert boardings == alightings
assert int(calculated_load.iloc[-1]) == 0
assert boardings == report["profile_accounted_passengers"]
assert int(calculated_load.max()) == report[
    "peak_ticket_observed_load"
]

peak = int(calculated_load.max())

peak_stops = df.loc[
    calculated_load == peak,
    ["stop_sequence_index", "stop_name"]
].to_dict(orient="records")

result = {
    "candidate_run_id": report["candidate_run_id"],
    "route": report["route"],
    "gtfs_pattern_candidate": report["gtfs_pattern_candidate"],
    "stops_validated": len(df),
    "total_boardings": boardings,
    "total_alightings": alightings,
    "peak_ticket_observed_load": peak,
    "first_peak_stop": peak_stops[0]["stop_name"],
    "all_peak_stops": peak_stops,
    "mathematical_validation_passed": True,
    "physical_trip_verified": False,
    "actual_bus_occupancy_verified": False,
    "metric": "estimated_ticket_observed_onboard_load"
}

path = OUT / "occupancy_validation_summary.json"

path.write_text(
    json.dumps(result, indent=2),
    encoding="utf-8"
)

print("OCCUPANCY VALIDATION SUMMARY SAVED")
print("=" * 45)
print("Run:", result["candidate_run_id"])
print("Stops:", result["stops_validated"])
print("Passengers:", result["total_boardings"])
print("Peak load:", result["peak_ticket_observed_load"])
print("First peak stop:", result["first_peak_stop"])
print("Saved:", path)
