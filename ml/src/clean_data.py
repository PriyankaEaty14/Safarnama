
from pathlib import Path
import pandas as pd

BASE = Path(__file__).resolve().parents[1]
RAW = BASE / "data" / "raw"
OUT = BASE / "data" / "processed"

OUT.mkdir(parents=True, exist_ok=True)

files = list(RAW.rglob("*.csv"))

if not files:
    raise FileNotFoundError("No CSV found in data/raw")

required = [
    "passenger_count",
    "vehicle_number",
    "start_stop_name",
    "end_stop_name",
    "route",
    "created_at"
]

cleaned = []
rejected = []

for file in files:
    print("Processing:", file.name)

    for chunk in pd.read_csv(
        file,
        chunksize=100000,
        low_memory=False
    ):
        chunk.columns = chunk.columns.str.strip()

        missing = set(required) - set(chunk.columns)

        if missing:
            raise ValueError(
                f"Missing columns: {missing}"
            )

        # Preserve original records
        chunk = chunk.copy()

        # Convert numeric fields
        chunk["passenger_count"] = pd.to_numeric(
            chunk["passenger_count"],
            errors="coerce"
        )

        # Parse timestamps
        chunk["created_at"] = pd.to_datetime(
            chunk["created_at"],
            errors="coerce"
        )

        # Standardize text
        for col in [
            "vehicle_number",
            "route",
            "start_stop_name",
            "end_stop_name"
        ]:
            chunk[col] = (
                chunk[col]
                .astype("string")
                .str.strip()
                .str.upper()
            )

        # Validate essential fields
        valid = (
            chunk["passenger_count"].notna()
            & (chunk["passenger_count"] > 0)
            & (chunk["passenger_count"] % 1 == 0)
            & chunk["created_at"].notna()
            & chunk["route"].notna()
            & chunk["vehicle_number"].notna()
            & chunk["start_stop_name"].notna()
        )

        good = chunk.loc[valid].copy()
        bad = chunk.loc[~valid].copy()

        # Extract time features
        good["date"] = good["created_at"].dt.date
        good["hour"] = good["created_at"].dt.hour
        good["day_of_week"] = (
            good["created_at"].dt.dayofweek
        )
        good["is_weekend"] = (
            good["day_of_week"] >= 5
        )

        cleaned.append(good)
        rejected.append(bad)

df = pd.concat(cleaned, ignore_index=True)
bad_df = pd.concat(rejected, ignore_index=True)

# Save data efficiently
df.to_parquet(
    OUT / "cleaned_tickets.parquet",
    index=False
)

bad_df.to_parquet(
    OUT / "rejected_tickets.parquet",
    index=False
)

print("\nCLEANING COMPLETE")
print("Valid records:", len(df))
print("Rejected records:", len(bad_df))
print("Unique routes:", df["route"].nunique())
print("Unique vehicles:", df["vehicle_number"].nunique())

print("\nMissing destination stops:")
print(df["end_stop_name"].isna().sum())

print("\nDate range:")
print(df["created_at"].min())
print(df["created_at"].max())
