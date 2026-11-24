# Member 2 backend completion

The baseline already included FastAPI routers, SQLite schema and ingestion,
calendar-aware journey planning, ordered-leg deduplication, geometry alignment
and a crowding-unavailable adapter. Its original 15 backend tests passed when
rerun before changes.

## Delivered

- The importer verifies Delhi agency time zones, records validation outcomes,
  detects backward times across partial schedules and builds a staged
  replacement database. The supplied feed imported 2 agencies, 6,862 stops,
  2,574 routes, 80,357 trips, 2,737,136 stop times and 965,607 shape points
  without rejected or duplicate rows. See the recorded ingestion report.
- Journey search uses the indexed boarding window and reuses second-leg
  candidates by transfer stop. It ranks eligible itineraries before building
  their leg responses. It preserves loop occurrences, distinct connections
  and inclusive six-hour boarding behavior. Feed-declared stop-level
  transfers and calendar exceptions are covered by fixtures because the Delhi
  ZIP lacks those files.
- The typed API now distinguishes a working database connection from schedule
  readiness. Known routes without a shape return an explicit unavailable
  status. The analytics endpoint returns schedule-based departures and
  directional corridors alongside record counts.
- The active crowding provider is still unavailable. The integration
  handoff documents how to validate a future provider.

## Scope of validation

The supplied feed uses Asia/Kolkata and publishes service dates between
2025-01-01 and 2040-01-01. Its trip `direction_id` field is blank. The planner
supports one interchange and stop-level transfer types 0–3. Route-specific,
trip-specific and in-seat transfer rules require further support for a feed
that uses them. The audited feed contains none of those types. The
deployment guide documents container operation and persistent feed refresh.
See [the testing report](TESTING_REPORT.md) for executed checks and
[Member 1 dependencies](MEMBER_1_DEPENDENCIES.md) for prediction work.
