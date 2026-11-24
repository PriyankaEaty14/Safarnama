
from pathlib import Path
import json
import pandas as pd
import matplotlib.pyplot as plt

BASE = Path(__file__).resolve().parents[1]
OUT = BASE / "outputs"
OUT.mkdir(parents=True, exist_ok=True)

df = pd.read_csv(
    OUT / "sample_occupancy_profile.csv"
)

# The load after each stop applies to the
# segment immediately following that stop.
segments = df.iloc[:-1].copy()

x = segments["stop_sequence_index"]
y = segments["ticket_observed_load"]

peak = int(y.max())
peak_row = segments.loc[y.idxmax()]

plt.figure(figsize=(14, 6))

plt.plot(
    x, y,
    linewidth=2.5,
    marker="o",
    markersize=3,
    color="#0D9488"
)

plt.fill_between(
    x, y,
    color="#0D9488",
    alpha=0.15
)

plt.scatter(
    [peak_row["stop_sequence_index"]],
    [peak],
    color="#DC2626",
    s=90,
    zorder=5
)

plt.annotate(
    f"Peak: {peak} passengers",
    xy=(peak_row["stop_sequence_index"], peak),
    xytext=(8, 18),
    textcoords="offset points",
    fontsize=11,
    fontweight="bold"
)

plt.title(
    "CrowdWise AI | Ticket-Observed Passenger Load\n"
    "Route 717AUP - Candidate Run DL1PD8407_48",
    fontsize=15,
    fontweight="bold"
)

plt.xlabel("GTFS Stop Sequence Index")
plt.ylabel("Ticket-Observed Onboard Passengers")
plt.grid(alpha=0.2)
plt.ylim(bottom=0)
plt.tight_layout()

chart_path = OUT / "sample_occupancy_chart.png"
plt.savefig(chart_path, dpi=200)
plt.close()

summary = {
    "route": "717AUP",
    "candidate_run_id": "DL1PD8407_48",
    "gtfs_trip_pattern": "2171_FULL_04_40",
    "ticket_records": 29,
    "supported_ticketed_passengers": 34,
    "excluded_ticketed_passengers": 0,
    "peak_ticket_observed_load": peak,
    "peak_stop_name": str(peak_row["stop_name"]),
    "stop_count": len(df),
    "metric_type": "ticket_observed_load",
    "is_actual_occupancy": False,
    "is_live_data": False
}

json_path = OUT / "sample_occupancy_summary.json"

with open(json_path, "w", encoding="utf-8") as f:
    json.dump(summary, f, indent=2)

print("\nVISUALIZATION COMPLETE")
print("=" * 45)
print("Chart:", chart_path)
print("Summary:", json_path)
print("Peak ticket-observed load:", peak)
print("First peak stop:", peak_row["stop_name"])
