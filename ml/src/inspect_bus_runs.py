
from pathlib import Path
import pandas as pd

BASE = Path(__file__).resolve().parents[1]
DATA = BASE / "data" / "processed"
OUT = BASE / "outputs"
OUT.mkdir(parents=True, exist_ok=True)

print("Loading candidate runs...")

df = pd.read_parquet(
    DATA / "candidate_bus_runs.parquet"
)

# Select a well-represented route
ROUTE = "717AUP"

route_df = df[df["route"] == ROUTE].copy()

print("\nROUTE ANALYSIS:", ROUTE)
print("=" * 50)

print("Ticket records:", len(route_df))
print("Unique vehicles:", route_df["vehicle_number"].nunique())
print("Candidate runs:", route_df["candidate_run_id"].nunique())

# Find runs with many ticket records
run_counts = (
    route_df.groupby("candidate_run_id")
    .size()
    .sort_values(ascending=False)
)

print("\nTop 10 candidate runs:")
print(run_counts.head(10))

# Inspect the run with the most tickets
if not run_counts.empty:
    selected_run = run_counts.index[0]

    sample = route_df[
        route_df["candidate_run_id"] == selected_run
    ].sort_values("created_at")

    print("\nSELECTED RUN:", selected_run)

    print(
        sample[
            [
                "vehicle_number",
                "route",
                "created_at",
                "start_stop_name",
                "end_stop_name",
                "start_stop_id",
                "end_stop_id",
                "passenger_count"
            ]
        ].to_string(index=False)
    )

    sample.to_csv(
        OUT / "sample_bus_run.csv",
        index=False
    )

print("\nSaved sample_bus_run.csv")
