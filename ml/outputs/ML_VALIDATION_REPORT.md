# CrowdWise AI — ML Validation Report

## 1. Objective
Estimate historical route-level ticketed passenger demand
and explore reconstruction of stop-segment passenger loads.

## 2. Data processing
Cleaned ETM records: 1,317,730.

Route-aware boarding-stop matching: 70.76%.
Route-aware destination-stop matching: 69.94%.
Both stops matched: 55.34%.

GTFS-compatible ordered journeys:
728,657 ticket records (55.30% of cleaned records).

GTFS compatibility means a stop pair occurs in the
correct order on at least one scheduled trip pattern.
It does not prove actual trip assignment.

## 3. Passenger load reconstruction
Example route: 717AUP
Candidate run: DL1PD8407_48
Selected GTFS pattern: 2171_FULL_04_40

Ticket records: 29
Ticketed passengers represented: 34
Passengers supported by selected pattern: 34
Excluded passengers: 0
Peak ticket-observed load: 15

This is an exploratory reconstruction, not a validated
estimate of actual bus occupancy.

## 4. Demand forecasting
Historical route x weekday x hour mean baseline.

Training period: October 1–24, 2026.
Holdout period: October 25–31, 2026.

### Full network
| Model | MAE | RMSE | WAPE |
|---|---:|---:|---:|
| Historical baseline | 0.549 | 1.539 | 58.19% |
| CatBoost | 0.672 | 1.978 | 71.30% |

### Top 20 routes selected from training demand
| Model | MAE | RMSE | WAPE |
|---|---:|---:|---:|
| Historical baseline | 4.243 | 6.900 | 29.52% |
| CatBoost | 6.542 | 11.290 | 45.51% |

The historical baseline was selected because it
outperformed CatBoost on the shared holdout set.

## 5. Validation limitations
The calendar includes route-hour combinations with
no recorded tickets and treats them as zero demand.
Missing data may therefore bias evaluation.

Overall MAE is influenced by numerous zero-demand hours.
Full-network WAPE was 58.19%, indicating substantial
remaining forecasting error.

Model selection used the holdout period, so the reported
results are not an independent post-selection test.

## 6. Deployment
The selected historical baseline was refitted on
October 1–31, 2026.

Exported 354,816 route-weekday-hour prediction records.
A 20-route demo subset contains 3,360 records.

Outputs describe historical ticketed demand only,
not live crowding, available seats or bus capacity.

## 7. Future improvements
- Validate ETM data coverage and rejected records.
- Review fuzzy stop matches.
- Align ticket timestamps with GTFS schedules.
- Reconstruct physical bus trips more reliably.
- Estimate stop-segment loads across multiple runs.
- Calibrate occupancy using known vehicle capacities
  and additional passenger-count observations.
