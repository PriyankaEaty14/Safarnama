from pathlib import Path
import pandas as pd

BASE = Path(__file__).resolve().parents[1]
path = BASE / "outputs" / "audited_candidate_occupancy_profile.csv"

df = pd.read_csv(path)

print("PROFILE COLUMNS")
print(df.columns.tolist())

print("\nFIRST FIVE ROWS")
print(df.head().to_string(index=False))

print("\nLAST FIVE ROWS")
print(df.tail().to_string(index=False))

print("\nPROFILE INFORMATION")
print("Rows:", len(df))
print("Missing values:")
print(df.isna().sum().to_string())
