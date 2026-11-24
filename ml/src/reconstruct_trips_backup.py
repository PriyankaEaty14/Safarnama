
from pathlib import Path
import pandas as pd

BASE = Path(__file__).resolve().parents[1]
DATA = BASE / "data" / "processed"
OUT = BASE / "outputs"
OUT.mkdir(parents=True, exist_ok=True)

print("Loading occupancy-ready tickets...")

df = pd.read_parquet(
    DATA / "occupancy_ready_tickets.parquet"
)

# Initial heuristic: a long gap between tickets
# may indicate a different bus run.
GAP_MINUTES = 45

# Sort each vehicle's records chronologically
df = df.sort_values(
    ["vehicle_number", "created_at"]
).copy()

groups = df.groupby("vehicle_number", sort=False)

previous_time = groups["created_at"].shift()
previous_route = groups["route"].shift()

gap_minutes = (
    df["created_at"] - previous_time
).dt.total_seconds() / 60

# Start a new candidate run when:
# - vehicle has no previous ticket
# - route changes
# - gap exceeds threshold
# - service date changes
new_run = (
    previous_time.isna()
    | df["route"].ne(previous_route)
    | (gap_minutes > GAP_MINUTES)
    | (
        df["created_at"].dt.date
        != previous_time.dt.date
    )
)

df["new_run"] = new_run.fillna(True)

df["run_number"] = (
    df.groupby("vehicle_number")["new_run"]
    .cumsum()
)

df["candidate_run_id"] = (
    df["vehicle_number"].astype(str)
    + "_"
    + df["run_number"].astype(str)
)

# Summarize candidate runs
summary = (
    df.groupby("candidate_run_id")
    .agg(
        vehicle=("vehicle_number", "first"),
        route=("route", "first"),
        first_ticket=("created_at", "min"),
        last_ticket=("created_at", "max"),
        ticket_count=("passenger_count", "size"),
        ticketed_passengers=("passenger_count", "sum"),
        boarding_stops=("start_stop_id", "nunique")
    )
    .reset_index()
)

summary["duration_minutes"] = (
    summary["last_ticket"]
    - summary["first_ticket"]
).dt.total_seconds() / 60

df.to_parquet(
    DATA / "candidate_bus_runs.parquet",
    index=False
)

summary.to_csv(
    OUT / "candidate_run_summary.csv",
    index=False
)

print("\nCANDIDATE BUS RUN RECONSTRUCTION")
print("=" * 45)

print("Ticket records:", len(df))
print("Candidate runs:", len(summary))

print("\nTicket counts per run:")
print(summary["ticket_count"].describe())

print("\nRun durations (minutes):")
print(summary["duration_minutes"].describe())

print("\nRuns with at least 5 tickets:",
      (summary["ticket_count"] >= 5).sum())

print("\nRuns with at least 10 tickets:",
      (summary["ticket_count"] >= 10).sum())

print("\nLongest candidate runs:")
print(
    summary.sort_values(
        "duration_minutes",
        ascending=False
    ).head(10).to_string(index=False)
)

print("\nSaved candidate_bus_runs.parquet")
print("Saved candidate_run_summary.csv")
