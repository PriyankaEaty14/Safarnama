
from pathlib import Path
import pandas as pd

BASE = Path(__file__).resolve().parents[1]
OUT = BASE / "outputs"

for filename in [
    "unmatched_boarding_stops.csv",
    "unmatched_destination_stops.csv"
]:
    print("\n" + "=" * 55)
    print(filename)
    print("=" * 55)

    df = pd.read_csv(OUT / filename)

    print("\nTop 30 unmatched names:")
    print(df.head(30).to_string(index=False))

# Check ambiguous GTFS stop names
stops = pd.read_csv(
    BASE / "data/raw/gtfs/stops.txt",
    dtype=str
)

stops["normalized"] = (
    stops["stop_name"]
    .str.upper()
    .str.strip()
    .str.replace(r"\s+", " ", regex=True)
)

duplicates = (
    stops.groupby("normalized")["stop_id"]
    .nunique()
)

print("\nAmbiguous GTFS names:")
print((duplicates > 1).sum())

print("\nMost frequently duplicated names:")
print(
    duplicates[duplicates > 1]
    .sort_values(ascending=False)
    .head(20)
)
