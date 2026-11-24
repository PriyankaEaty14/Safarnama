
from pathlib import Path
import json
import pandas as pd

BASE = Path(__file__).resolve().parents[1]
OUT = BASE / "outputs"


def load_json(name):
    return json.loads(
        (OUT / name).read_text(encoding="utf-8")
    )


master = load_json(
    "multi_run_occupancy_summary_v2.json"
)

profiles = pd.read_csv(
    OUT / "multi_run_occupancy_profiles_v2.csv",
    dtype={"stop_id": str}
)

runs = {
    row["candidate_run_id"]: row
    for row in master["runs"]
}

assert len(runs) == master["candidate_runs_analyzed"]

checked_patterns = 0
expected_profile_rows = 0

for run_id, run in runs.items():

    assert run["physical_trip_verified"] is False
    assert run["actual_bus_occupancy_verified"] is False

    assert len(run["patterns"]) == (
        run["equally_supported_patterns"]
    )

    for pattern in run["patterns"]:

        pattern_id = pattern["pattern_id"]

        rows = profiles[
            (profiles["candidate_run_id"] == run_id)
            & (profiles["pattern_id"] == pattern_id)
        ].sort_values("stop_sequence_index")

        assert len(rows) == pattern["stop_count"]

        assert rows["stop_sequence_index"].tolist() == (
            list(range(pattern["stop_count"]))
        )

        lower = rows["ticket_load_lower_bound"]
        upper = rows["ticket_load_upper_bound"]

        assert (lower >= 0).all()
        assert (upper >= lower).all()

        assert lower.iloc[-1] == 0
        assert upper.iloc[-1] == 0

        assert int(lower.max()) == (
            pattern["peak_load_lower_bound"]
        )

        assert int(upper.max()) == (
            pattern["peak_load_upper_bound"]
        )

        assert rows["unambiguous_boardings"].sum() == (
            pattern["unambiguous_passengers"]
        )

        assert rows["unambiguous_alightings"].sum() == (
            pattern["unambiguous_passengers"]
        )

        reconstructed = (
            rows["unambiguous_boardings"]
            - rows["unambiguous_alightings"]
        ).cumsum()

        assert (
            reconstructed
            == rows["unambiguous_ticket_load"]
        ).all()

        assert (
            pattern["supported_ticketed_passengers"]
            + pattern["excluded_passengers"]
            == run["total_ticketed_passengers"]
        )

        assert all(
            pattern["validation_checks"].values()
        )

        checked_patterns += 1
        expected_profile_rows += len(rows)

assert len(profiles) == expected_profile_rows
assert checked_patterns > 0

checked_reports = 0

for sample_path in OUT.glob(
    "sample_occupancy_summary_v2_*.json"
):

    sample = load_json(sample_path.name)

    run_id = sample["candidate_run_id"]

    if run_id not in master["requested_run_ids"]:
        continue

    validation_name = sample_path.name.replace(
        "sample_occupancy_summary",
        "occupancy_validation_summary"
    )

    validation = load_json(validation_name)

    for key, value in runs[run_id].items():
        assert sample[key] == value
        assert validation[key] == value

    assert validation["legacy_pattern_comparison"] == (
        master["legacy_pattern_comparison"]
    )

    checked_reports += 1

assert checked_reports == len(
    set(master["requested_run_ids"])
)

print("\nREPORT CONSISTENCY VERIFICATION")
print("=" * 50)
print("Candidate runs checked:", len(runs))
print("GTFS patterns checked:", checked_patterns)
print("Profile rows checked:", expected_profile_rows)
print("Sample/validation report pairs:", checked_reports)
print("Passenger accounting: PASSED")
print("Load balance: PASSED")
print("Cross-report consistency: PASSED")
print("Physical trip validation: NOT ESTABLISHED")
print("\nALL REPORT CONSISTENCY CHECKS PASSED")
