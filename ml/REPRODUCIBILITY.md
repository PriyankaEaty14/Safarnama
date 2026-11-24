# SAFARNAMA — ML Reproducibility Guide

## 1. Project overview

SAFARNAMA is a crowdedness-aware journey planning project developed for Transport Stack Hackathon 2026, Problem Statement 2.

The ML component uses October 2026 Delhi ETM ticketing records and static GTFS schedules to produce historical route-hour demand estimates and experimental ticket-derived load profiles.

## 2. Environment setup

Run the following commands from the `ml` directory:

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
```

The `requirements-lock.txt` file records the tested development environment.

## 3. Expected raw data structure

```text
ml/
  data/
    raw/
      October-Delhi.csv
      gtfs/
        routes.txt
        trips.txt
        stops.txt
        stop_times.txt
    processed/
  src/
  tests/
  outputs/
```

Only authorized ETM input CSV files should be placed
inside data/raw/, because clean_data.py recursively
discovers CSV files.

Detailed vehicle-level reconstruction outputs are
generated locally and intentionally excluded from Git.

The full handoff generator requires locally generated
research reports. The committed demo prediction CSV,
schema and examples support backend use without them.

Raw datasets must be obtained through the authorized hackathon data source. They are not distributed through this repository.

## 4. Quick-start backend integration

The committed demo prediction dataset enables backend integration without downloading or processing the original ETM dataset.

```powershell
python src/safarnama_predictor.py --route 717AUP --datetime "2026-11-27T08:00:00+05:30"
```

The expected historical prediction is 82.6 ticketed passengers per route-hour.

This is not actual onboard occupancy.

## 5. Stop-matching pipeline

The existing stop-matching pipeline is preserved.

```powershell
python src/clean_data.py
python src/build_route_stops.py
python src/match_stops.py
python src/match_stops_v2.py
python src/validate_stop_order.py
python src/build_stop_matches_v3.py
python src/validate_stop_order_v3.py
python src/compare_v2_v3.py
python src/validate_v3_mapping_integrity.py
```

## 6. Experimental load reconstruction

The V2 ordered ticket dataset is retained for reproducibility of the existing candidate-run experiments.

```powershell
python src/prepare_occupancy.py
python src/reconstruct_trips.py
python src/reconstruct_occupancy_v2.py --max-runs 20 --min-tickets 10 --run-id DL1PD8407_48
python src/verify_occupancy_reports_v2.py
python src/analyze_run_sensitivity.py
```

Candidate runs are heuristic groupings, not independently verified physical trips.

Repeated-stop ambiguity is represented using conditional ticket-load bounds.

## 7. Matching-quality audit

```powershell
python src/audit_matching_quality.py
python src/finalize_matching_review.py
```

The second command records the reviewed sample findings. Its review identifiers and expected names must correspond to the original deterministic sample.

Name consistency is reported separately from geographic accuracy.

## 8. Historical demand forecasting

```powershell
python src/build_hourly_demand.py
python src/evaluate_hourly_demand.py
python src/export_predictions.py
python src/prepare_backend_handoff.py
```

Additional comparison experiments:

```powershell
python src/build_hourly_demand_v2.py
python src/evaluate_hourly_demand_v2.py
python src/evaluate_hybrid_demand.py
```

The historical route-weekday-hour mean remains the selected model.

CatBoost is retained as a comparison experiment rather than the deployed model.

## 9. Generate final handoff documents

```powershell
python src/generate_final_handoff.py
```

Generated deliverables:

- SAFARNAMA_BACKEND_HANDOFF.md
- SAFARNAMA_FINAL_ML_REPORT.md
- safarnama_prediction_schema.json
- safarnama_prediction_manifest.json
- safarnama_api_examples.json

## 10. Automated validation

```powershell
python -m compileall -q src
python -m pytest -q
```

Recorded development result: 43 tests passed in 3.49 seconds.

This establishes successful execution of the current automated test suite, not independent physical occupancy validation.

## 11. Final recorded results

| Metric | Result |
|---|---:|
| Cleaned ticket records | 1,317,730 |
| Cleaned ticketed passengers | 1,422,016 |
| V2 both-stop matching coverage | 55.3409% |
| V3 both-stop matching coverage | 62.8224% |
| V3 GTFS-ordered journeys | 826,960 |
| Additional ordered journeys | 98,303 |
| Manual name-review samples | 45 |
| Name-consistent samples | 42 |
| Substantive name conflicts | 3 |
| Candidate-run sensitivity experiments | 15 |
| Multi-run reconstruction samples | 20 |
| Best-supported patterns examined | 21 |
| Demo prediction routes | 20 |
| Demo prediction rows | 3,360 |
| Automated tests passed | 43 |

## 12. Limitations

- Geographic stop-matching precision is not independently established.
- Physical vehicle-trip identity is unverified.
- Historical ticket demand is not actual bus occupancy.
- Vehicle capacity and remaining seats are unavailable.
- Prediction intervals are not calibrated.
- Future segment-level crowding forecasts are not implemented.
- No-transaction hours may be represented by zero-filled historical observations.

The backend must preserve these distinctions when displaying predictions.

## 13. Reproducibility status

Individual pipeline stages and the final integration test suite have been executed successfully during development. A complete clean-environment regeneration should be performed before claiming independently verified end-to-end reproducibility.