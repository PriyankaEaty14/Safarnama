# SAFARNAMA integration report

The source publication omits exploratory generated CSVs. The verified local
integration archive includes the unmodified Member 1 snapshot. The
repository retains the runtime prediction CSV, schema, manifest,
response examples and written validation evidence. The omitted files
are listed at the end of this report.

## Repository audit

`SAFARNAMA-complete.zip` provided a working React planner, FastAPI backend,
GTFS route and schedule queries, a route explorer, schedule analytics and a
crowding provider that returned a general unavailable response. It did not
resolve the crowding request's GTFS context or expose historical ticket
demand. `Safarnama-main (1).zip` provided the original Member 1 `ml/` tree.
It contained an executable predictor, lookup, schema, manifest, 3,360-row
export, evaluation materials and automated tests. The full network export,
original ETM datasets and reconstructed load artifacts suitable for
production segment forecasts were absent.

The work uses the two attached snapshots and the existing imported Delhi
GTFS database. The archive's normalized LF CSV differs from the manifest's
CRLF byte digest. Exact LF-to-CRLF verification matches the recorded hash.
The adapter recognizes that specific transport transformation without
rewriting the data.

## Integration completed

- **Member 1** supplied the unchanged weekday/hour historical mean predictor.
  The release combines all 86 of the supplied ML source, documentation,
  tests and artifact files byte-for-byte. The deployed runtime uses only the
  two inference modules, the CSV, the manifest and the response schema.
- **Member 2** loads the predictor once at startup, verifies inputs and
  checks a one-to-one route crosswalk against installed GTFS route IDs,
  agencies and exact directional names. Missing or corrupt data disables
  historical demand without disabling schedule planning. Crowding resolves
  the validated GTFS leg context and retains the unavailable provider.
- **Member 3** requests route-hour historical demand when journey details
  expand, using each scheduled boarding date/hour in Delhi. Requests for
  identical route/day/hour data inside a journey are shared. Old requests
  are cancelled on collapse or input changes. Loading, empty, and request
  error states do not show stale estimates. The itinerary separately
  displays unavailable segment crowding.

## Application files changed

| File | Change |
|---|---|
| `.env.example` | Documents the frontend historical-demand API path. |
| `backend/.env.example` | Documents the optional artifact override and disable setting. |
| `backend/Dockerfile` | Packages the original inference sources and required artifacts. |
| `backend/requirements.txt` | Adds the predictor's pandas and JSON Schema runtime dependencies. |
| `compose.yaml` | Configures optional historical artifact loading. |
| `backend/app/adapters/delhi_route_mapping.json` | Adds the explicit 20-route GTFS-to-ETM crosswalk and source feed hash. |
| `backend/app/adapters/historical_demand.py` | Validates artifacts, mapping and predictor responses and serves one loaded model. |
| `backend/app/api/crowding.py` | Validates route or journey context and reports per-leg availability. |
| `backend/app/api/historical_demand.py` | Adds the typed historical demand endpoint and unavailable states. |
| `backend/app/core/config.py` | Resolves runtime artifact configuration. |
| `backend/app/main.py` | Initializes the two providers and registers the new API. |
| `backend/app/services/crowding_service.py` | Rejects malformed estimates and degrades safely. |
| `backend/app/services/segment_context.py` | Resolves GTFS direction, stop order, trip schedules and service dates. |
| `backend/tests/test_ml_integration.py` | Adds historical demand and GTFS context regressions. |
| `src/api.js` | Centralizes the historical demand request. |
| `src/historical-demand.jsx` | Adds the separate historical demand section with provenance. |
| `src/main.jsx` | Integrates the section in journey details and labels unavailable crowding. |
| `src/styles.css` | Styles the new section within the existing responsive layout. |
| `tests/safarnama.spec.js` | Tests actual mapped demand, loading and request-failure behavior in Chromium. |
| `README.md`, `backend/README.md` | Document setup and a real example route. |
| `KNOWN_ISSUES.md`, `ML_HANDOFF.md` | Record current limits and direct readers to the integrated handoff. |
| `docs/API_CONTRACT.md` | Documents endpoint inputs, example responses and availability semantics. |
| `docs/DEPLOYMENT_GUIDE.md` | Documents deployment configuration and fail-closed operation. |
| `docs/ML_INTEGRATION_HANDOFF.md` | Records forecast provenance, crosswalk and checksum evidence. |
| `docs/INTEGRATION_REPORT.md` | Records the audit, implementation, and verification. |
| `ml/` | Adds all original files from the Member 1 snapshot. No bytes in those files were modified. |

## API examples

- `GET /api/v1/demand/historical?route_id=2171&date=2026-11-27&time=08:35`
  returned a historical estimate of 82.6 ticketed passengers per route-hour.
  Route label 717AUP, historical standard deviation 27.68, five calendar
  days and source `October_2026_ETM_historical_baseline` were returned.
- `GET /api/v1/crowding?route_id=2171&from_stop_id=2640&to_stop_id=3250&date=2026-11-27&time=08:35`
  returned the validated route and ordered stops with `status=unavailable`.
  Load, confidence, category and capacity were null.
- The [API contract](API_CONTRACT.md) includes full JSON examples and
  expected 404/422 and historical availability responses.

## Test results

| Command or check | Baseline | Integrated |
|---|---|---|
| `python -m pytest -q tests` from `ml/` | 43 passed | 43 passed |
| `python src/test_real_predictions.py` from `ml/` | — | Delivered dataset and direct lookup matched. |
| `python -m pytest -q` from `backend/` | 20 passed | 28 passed |
| `npm test` with the Delhi GTFS application and installed Chromium | 6 passed | 7 passed against the production frontend build with both local and Docker backends |
| `npm run build` | — | Passed. Two non-fatal React Router directive warnings. |
| `docker compose config -q` | — | Passed |
| Backend Docker image build and read-only Delhi database smoke test | — | Passed. Readiness and historical estimate verified. |
| Compare live historical API with Member 1 CSV for all mapped routes | — | 20 of 20 mapped route results matched. |

The first ML pytest invocation from the application root could not import
Member 1's `src` modules. Running the suite from its documented `ml/`
directory resolved it. Early integration tests surfaced the newline
checksum mismatch and passed after byte-equivalence validation. The first
attempt to start a fresh Docker container ran out of space. Removing
rebuildable build cache freed enough space and the retry succeeded.
The data-preparation diagnostic `ml/src/test_component_matching.py`
requires the upstream processed `ml/data/processed/route_stops.parquet`
artifact. It was absent from the source snapshots and the diagnostic is
outside the runtime integration tests.

## Launch readiness

Verified for local demonstration with the supplied GTFS database and the
20-route historical export. The backend also passed a containerized smoke
test. Public hosting, production traffic load, and monitoring are outside
this run. Full-network demand requires Member 1's export and a separately
validated mapping. Live occupancy, segment forecasting, capacity and seat
availability require additional validated data.

## Member 1 files imported unchanged

- `ml/.gitignore`
- `ml/README.md`
- `ml/REPRODUCIBILITY.md`
- `ml/outputs/FORECAST_MODEL_DECISION.md`
- `ml/outputs/ML_README.md`
- `ml/outputs/ML_VALIDATION_REPORT.md`
- `ml/outputs/SAFARNAMA_BACKEND_HANDOFF.md`
- `ml/outputs/SAFARNAMA_FINAL_ML_REPORT.md`
- `ml/outputs/candidate_run_sensitivity_v2.csv`
- `ml/outputs/candidate_run_sensitivity_v2.json`
- `ml/outputs/component_matching_diagnostic.csv`
- `ml/outputs/demo_route_predictions.csv`
- `ml/outputs/legacy_pattern_comparison_v2.json`
- `ml/outputs/manual_matching_review_summary.json`
- `ml/outputs/manual_matching_sample_metadata.json`
- `ml/outputs/matching_coverage_audit.json`
- `ml/outputs/matching_method_statistics.csv`
- `ml/outputs/route_matching_failures.csv`
- `ml/outputs/route_statistics.csv`
- `ml/outputs/route_validation_summary.csv`
- `ml/outputs/safarnama_api_examples.json`
- `ml/outputs/safarnama_prediction_manifest.json`
- `ml/outputs/safarnama_prediction_schema.json`
- `ml/outputs/stop_candidate_review.csv`
- `ml/outputs/ticket_exclusion_audit.csv`
- `ml/outputs/ticket_exclusion_audit.json`
- `ml/outputs/unmatched_boarding_stops.csv`
- `ml/outputs/unmatched_destination_stops.csv`
- `ml/outputs/unmatched_stop_diagnosis.csv`
- `ml/outputs/v3_stop_name_review.csv`
- `ml/requirements-lock.txt`
- `ml/requirements.txt`
- `ml/src/analyze_run_sensitivity.py`
- `ml/src/audit_data.py`
- `ml/src/audit_matching_quality.py`
- `ml/src/audit_ticket_exclusions.py`
- `ml/src/audit_v3_recovered_matches.py`
- `ml/src/build_hourly_demand.py`
- `ml/src/build_hourly_demand_v2.py`
- `ml/src/build_route_stops.py`
- `ml/src/build_stop_matches_v3.py`
- `ml/src/check_audited_profile.py`
- `ml/src/check_cleaned.py`
- `ml/src/clean_data.py`
- `ml/src/compare_v2_v3.py`
- `ml/src/demand_lookup.py`
- `ml/src/diagnose_stop_matching.py`
- `ml/src/estimate_occupancy.py`
- `ml/src/evaluate_hourly_demand.py`
- `ml/src/evaluate_hourly_demand_v2.py`
- `ml/src/evaluate_hybrid_demand.py`
- `ml/src/evaluate_routes.py`
- `ml/src/export_predictions.py`
- `ml/src/finalize_matching_review.py`
- `ml/src/generate_final_handoff.py`
- `ml/src/generate_ml_docs.py`
- `ml/src/inspect_bus_runs.py`
- `ml/src/inspect_data.py`
- `ml/src/inspect_gtfs.py`
- `ml/src/inspect_stop_candidates.py`
- `ml/src/inspect_unmatched.py`
- `ml/src/match_stops.py`
- `ml/src/match_stops_v2.py`
- `ml/src/occupancy_engine_v2.py`
- `ml/src/prepare_backend_handoff.py`
- `ml/src/prepare_occupancy.py`
- `ml/src/reconstruct_occupancy_v2.py`
- `ml/src/reconstruct_trips.py`
- `ml/src/reconstruct_trips_backup.py`
- `ml/src/review_v3_stop_names.py`
- `ml/src/safarnama_predictor.py`
- `ml/src/save_occupancy_validation.py`
- `ml/src/test_component_matching.py`
- `ml/src/test_real_predictions.py`
- `ml/src/train_catboost.py`
- `ml/src/validate_candidate_run.py`
- `ml/src/validate_occupancy_math.py`
- `ml/src/validate_stop_order.py`
- `ml/src/validate_stop_order_v3.py`
- `ml/src/validate_v3_mapping_integrity.py`
- `ml/src/verify_occupancy_reports_v2.py`
- `ml/src/visualize_occupancy.py`
- `ml/tests/test_demand_lookup.py`
- `ml/tests/test_occupancy_engine_v2.py`
- `ml/tests/test_safarnama_predictor.py`
- `ml/tests/test_safarnama_schema.py`

## Generated CSVs omitted from the source publication

- `ml/outputs/candidate_run_sensitivity_v2.csv`
- `ml/outputs/component_matching_diagnostic.csv`
- `ml/outputs/matching_method_statistics.csv`
- `ml/outputs/route_matching_failures.csv`
- `ml/outputs/route_statistics.csv`
- `ml/outputs/route_validation_summary.csv`
- `ml/outputs/stop_candidate_review.csv`
- `ml/outputs/ticket_exclusion_audit.csv`
- `ml/outputs/unmatched_boarding_stops.csv`
- `ml/outputs/unmatched_destination_stops.csv`
- `ml/outputs/unmatched_stop_diagnosis.csv`
- `ml/outputs/v3_stop_name_review.csv`
