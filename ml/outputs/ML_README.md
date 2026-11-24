# CrowdWise AI — Machine Learning Module

## Purpose
Estimate historical ticketed passenger demand by route,
day of week and hour, and demonstrate reconstruction
of ticket-observed onboard passenger loads.

## Dataset
Delhi ETM ticketing records, October 2026.
- Cleaned ticket records: 1,317,730
- Candidate GTFS-valid ticket records: 728,657
- Routes in demand baseline: 2,112
- GTFS stops: 6,862

## Selected forecasting method
Historical mean grouped by:
- Route
- Day of week (Monday=0, Sunday=6)
- Hour (0–23, Asia/Kolkata)

Predicted value:
Average ticketed passengers per route-hour.

This is NOT live bus occupancy.

## Main outputs
- outputs/hourly_demand_predictions.json
- outputs/demo_route_predictions.csv
- outputs/hourly_demand_baseline.csv
- outputs/sample_occupancy_profile.csv
- outputs/sample_occupancy_summary.json
- outputs/sample_occupancy_chart.png

## Backend lookup
Input: route, day_of_week, hour
Output: predicted_passengers, daily_std, observed_days

Example:
route=717AUP, day_of_week=4, hour=8

Expected historical demand: 82.6 passengers/hour.

## Interpretation
Historical demand describes ticketed passenger activity
across an entire route during one hour.

The sample occupancy profile estimates onboard ticketed
passengers along one candidate bus journey.

These are different metrics and must not be confused.

## Known limitations
- Some ETM ticket records were excluded during cleaning.
- Stop matching is incomplete and includes fuzzy matches.
- Vehicle run boundaries are heuristic.
- ETM records do not directly identify physical bus trips.
- Ticket timestamps are not verified boarding timestamps.
- GTFS trip patterns are not yet time-aligned to tickets.
- Missing ETM records may be interpreted as zero demand.
- Unticketed passengers are not captured.
- Bus capacity is unknown.
- No real-time occupancy information is available.

## Reproducibility
Run scripts from the ml directory using:

.\.venv\Scripts\python.exe src\build_hourly_demand.py
.\.venv\Scripts\python.exe src\evaluate_hourly_demand.py
.\.venv\Scripts\python.exe src\evaluate_routes.py
.\.venv\Scripts\python.exe src\train_catboost.py
.\.venv\Scripts\python.exe src\export_predictions.py
.\.venv\Scripts\python.exe src\prepare_backend_handoff.py

These scripts require the processed input datasets.
