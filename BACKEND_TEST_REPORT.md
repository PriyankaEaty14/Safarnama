# Backend test report

This document records an earlier project milestone. See the [current verification and status](docs/FINAL_TEST_REPORT.md) for the latest evidence.

This archive records the pre-update state. See the [current testing report](docs/TESTING_REPORT.md).

## Checks run

- Baseline before repair: `pytest -q` — 2 passed, 1 dependency warning.
- Final targeted pass: `/workspace/work/.venv/bin/python -m pytest -q` from
  `backend/` — 15 passed, 0 failed, 0 skipped, 1 Starlette/httpx deprecation
  warning (23 November 2026).
- Live backend health on port 8765 returned
  `{"status":"ok","database":"ok"}`.
- Live `/openapi.json` loaded with 11 paths, including health, stops,
  journeys, crowding, analytics and routes.
- Real-feed search `917` to `365` at 08:35 on 23 November 2026 returned
  12 distinct journey options after duplicate bus-pair removal. A sample
  option arrived at minute 562 (09:22) with one transfer. This search took
  about 4.7 seconds in the local test client.
- Real-feed geometry requests returned 43 and 152 shape points for the two
  legs of a sampled transfer journey; a direct segment returned 46 points.

## Covered behavior

The synthetic GTFS tests cover importer rejection categories, duplicate
detection, repeat import, atomic failure, calendar exceptions and weekends,
direct/transfer journeys, candidate positions beyond former 25/100 limits,
transfer timing, midnight crossing, balanced ranking, loop geometry, missing
shape behavior, crowding contract validation, and API response shape. The
targeted pass added regression tests for two distinct transfer stops on the
same bus pair, repeated direct destination occurrences, and the inclusive
six-hour boarding boundary for both first and second buses. Journey IDs now
include the ordered leg stop IDs and stop sequences.

The small fixture does not benchmark worst-case network search, prove all
possible Delhi shape alignments, or validate ML predictions. No ML occupancy
model is integrated.
