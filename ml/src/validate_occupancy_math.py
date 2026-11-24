
from pathlib import Path
import pandas as pd

BASE = Path(__file__).resolve().parents[1]

path = (
    BASE / "outputs"
    / "audited_candidate_occupancy_profile.csv"
)

df = pd.read_csv(path)

print("VALIDATING OCCUPANCY PROFILE")
print("=" * 50)

required = [
    "stop_sequence_index",
    "stop_id",
    "boardings",
    "alightings",
    "ticket_observed_load",
    "stop_name"
]

assert all(col in df.columns for col in required)
assert not df[required].isna().any().any()

# Check stop sequence
assert df["stop_sequence_index"].tolist() == list(
    range(len(df))
), "Invalid stop sequence"

# Check passenger counts
for column in [
    "boardings",
    "alightings",
    "ticket_observed_load"
]:
    assert (df[column] >= 0).all(), (
        f"Negative values found in {column}"
    )

    assert (df[column] % 1 == 0).all(), (
        f"Non-integer values found in {column}"
    )

# Recalculate onboard passengers
expected_load = (
    df["boardings"] - df["alightings"]
).cumsum()

assert (
    expected_load == df["ticket_observed_load"]
).all(), "Occupancy calculation mismatch"

# Check passenger conservation
total_boardings = int(df["boardings"].sum())
total_alightings = int(df["alightings"].sum())

assert total_boardings == total_alightings, (
    "Boardings and alightings do not balance"
)

assert total_boardings == 34, (
    "Expected 34 ticketed passengers"
)

# Check final onboard count
assert df.iloc[-1]["ticket_observed_load"] == 0, (
    "Passengers remain onboard after final stop"
)

peak = int(df["ticket_observed_load"].max())

peak_stops = df[
    df["ticket_observed_load"] == peak
]

print("Stops validated:", len(df))
print("Total boardings:", total_boardings)
print("Total alightings:", total_alightings)
print("Final load:", int(df.iloc[-1]["ticket_observed_load"]))
print("Peak ticket-observed load:", peak)

print("\nStops with maximum load:")
print(
    peak_stops[
        ["stop_sequence_index", "stop_name"]
    ].to_string(index=False)
)

print("\nALL OCCUPANCY MATHEMATICAL CHECKS PASSED!")
