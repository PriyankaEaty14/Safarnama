
from pathlib import Path
import pandas as pd

# Locate the dataset folder
BASE = Path(__file__).resolve().parents[1]
DATA = BASE / "data" / "raw"

files = list(DATA.rglob("*.csv"))

if not files:
    print("ERROR: No CSV file found!")
    print("Place the extracted CSV in data/raw/")
    raise SystemExit

for file in files:
    print("\nDATASET:", file.name)

    df = pd.read_csv(
        file,
        nrows=10000,
        low_memory=False
    )

    print("\n1. Shape:")
    print(df.shape)

    print("\n2. Column names:")
    print(df.columns.tolist())

    print("\n3. First five rows:")
    print(df.head().to_string())

    print("\n4. Missing values:")
    print(df.isnull().sum())

    print("\n5. Data types:")
    print(df.dtypes)

    print("\n6. Duplicate rows in sample:")
    print(df.duplicated().sum())

    if "route" in df.columns:
        print("\n7. Unique routes in sample:")
        print(df["route"].nunique())

    if "created_at" in df.columns:
        print("\n8. Timestamp examples:")
        print(df["created_at"].head())

print("\nInspection completed!")
