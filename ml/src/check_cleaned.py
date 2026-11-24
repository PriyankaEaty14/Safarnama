
from pathlib import Path
import pandas as pd

BASE = Path(__file__).resolve().parents[1]

file = BASE / "data/processed/cleaned_tickets.parquet"

df = pd.read_parquet(file)

print("Total valid tickets:", len(df))

print("\nTotal passengers:")
print(df["passenger_count"].sum())

print("\nTop 10 routes:")
print(df["route"].value_counts().head(10))

print("\nPassenger demand by hour:")
print(
    df.groupby("hour")["passenger_count"]
    .sum()
    .sort_index()
)

print("\nWeekday vs weekend passengers:")
print(
    df.groupby("is_weekend")["passenger_count"]
    .sum()
)

print("\nMissing destination stops:")
print(df["end_stop_name"].isna().sum())
