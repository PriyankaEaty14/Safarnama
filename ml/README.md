# SAFARNAMA — Machine Learning Module

**Transport Stack Hackathon 2026 | Problem Statement 2 — Crowdedness-Aware Journey Planner**

## Overview

SAFARNAMA uses historical Delhi Electronic Ticketing Machine (ETM) records and General Transit Feed Specification (GTFS) schedules to support data-informed journey planning.

The ML module provides:

- Historical route-hour ticket demand predictions.
- Route-aware ETM-to-GTFS stop matching.
- Experimental ticket-derived load reconstruction.
- Repeated-stop ambiguity handling.
- Candidate-run sensitivity analysis.
- A standardized backend prediction interface.
- Formal JSON response validation.

Historical ticket demand is not actual bus occupancy, live crowdedness or remaining seat availability.

## Key results

| Metric | Result |
|---|---:|
| Cleaned ticket records | 1,317,730 |
| Ticketed passengers | 1,422,016 |
| ETM routes | 2,112 |
| V2 both-stop matching coverage | 55.34% |
| V3 both-stop matching coverage | 62.82% |
| V3 GTFS-ordered journeys | 826,960 |
| Additional ordered journeys | 98,303 |
| Name-review samples | 45 |
| Name-consistent mappings | 42 |
| Substantive name conflicts | 3 |
| Candidate-run sensitivity experiments | 15 |
| Experimental candidate runs evaluated | 20 |
| GTFS patterns evaluated | 21 |
| Backend demo routes | 20 |
| Backend prediction rows | 3,360 |
| Automated tests passed | 43 |

Stop-matching coverage and name consistency do not establish geographic matching accuracy.

## Selected forecasting model

The historical route-weekday-hour mean was selected after chronological evaluation against CatBoost.

Training period: October 1–24, 2026.

Evaluation period: October 25–31, 2026.

### Top-20 training-demand route evaluation

| Metric | Historical baseline | CatBoost |
|---|---:|---:|
| MAE | 4.243 | 6.542 |
| RMSE | 6.900 | 11.290 |
| WAPE | 29.52% | 45.51% |

Lower values indicate better performance.

The evaluation period was reused for model comparisons and is not an untouched final test set. The deployment baseline was refitted using all October data.

## Quick start

Run from the ml directory:

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python -m pytest -q
```

Recorded development test result: 43 passed.

## Backend integration

The committed demo prediction dataset supports integration without requiring access to the original ETM records.

```python
from src.safarnama_predictor import SafarnamaPredictor

predictor = SafarnamaPredictor()

result = predictor.predict(
    route="717AUP",
    applicable_datetime="2026-11-27T08:00:00+05:30"
)

print(result)
```

Initialize the predictor once during backend startup.

### Example result

- Route: 717AUP
- Direction: UP
- Applicable hour: Friday, 08:00 IST
- Historical ticket demand: 82.6 passengers per route-hour
- Historical daily standard deviation: 27.68
- Historical calendar-day samples: 5
- Calibrated confidence interval: unavailable
- Actual occupancy: unavailable
- Remaining seats: unavailable

Missing predictions return null, not zero.

Zero-valued historical predictions do not guarantee empty buses.

## Command-line interface

```powershell
python src/safarnama_predictor.py --route 717AUP --datetime "2026-11-27T08:00:00+05:30"
```

The interface supports timezone conversion, directional route identifiers and optional boarding and alighting stop context.

Stop context does not constitute a segment-level forecast.

## Experimental load reconstruction

The generalized reconstruction engine groups identical GTFS stop sequences using canonical pattern identifiers.

Repeated-stop ambiguity is represented using conditional ticket-load bounds rather than forcing an arbitrary earliest occurrence.

The original 45-minute candidate-run grouping threshold remains an exploratory assumption. Sensitivity analysis was performed using 15, 30, 45, 60 and 90-minute thresholds.

Candidate runs are not independently verified physical bus trips.

## Documentation

- [Backend integration guide](outputs/SAFARNAMA_BACKEND_HANDOFF.md)
- [Final technical validation report](outputs/SAFARNAMA_FINAL_ML_REPORT.md)
- [JSON response schema](outputs/safarnama_prediction_schema.json)
- [Prediction dataset manifest](outputs/safarnama_prediction_manifest.json)
- [Example responses](outputs/safarnama_api_examples.json)
- [Reproducibility guide](REPRODUCIBILITY.md)
- [Forecast model decision](outputs/FORECAST_MODEL_DECISION.md)

## Data availability and privacy

Original ETM datasets, processed ticket records, vehicle-level reconstruction outputs and large intermediate files are maintained locally.

Access to original datasets is subject to the hackathon data-sharing terms.

## Known limitations

- Independent geographic stop-matching accuracy is not established.
- Candidate vehicle runs are not confirmed physical trips.
- Ticket issue times may differ from actual boarding times.
- Pass holders and other riders may not appear in ETM records.
- No-transaction hours may be zero-filled.
- Vehicle capacity and seated passenger counts are unavailable.
- Live occupancy data is unavailable.
- Prediction uncertainty is not calibrated.
- Future segment-level crowdedness forecasts are not implemented.

The current ML deliverable provides a validated historical demand interface and experimental ticket-derived load reconstruction, forming a foundation for further crowdedness-aware journey planning.