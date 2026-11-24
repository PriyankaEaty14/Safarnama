# SAFARNAMA repository audit

## Recovered baseline

Baseline: `6de8b403a1efd0efa89070b6488ceeb73aef26b8` on `main`.
The recovered checkout was clean and the GitHub branch pointed to the same
commit. Development uses that history.

- React/Vite serves planner, explorer and analytics routes, through a shared
  Axios client. Leaflet uses imported shape and stop coordinates. Recharts
  plots timetable statistics. Expanded results display historical ticket
  demand separately from the crowding status.
- FastAPI serves versioned stops, routes, trip and geometry lookups, journeys,
  crowding, demand, analytics and database probes. SQLite uses indexed trip
  and stop times, transactional GTFS import and atomic file replacement.
  The planner handles direct and one-transfer results, calendar exceptions,
  transfers across midnight and ordered stops.
- Member 1 ships a weekday/hour mean predictor, checked manifest and schema,
  and a demo historical export. The full export, raw October ETM data, and
  ground-truth per-vehicle passenger observations are absent. Exploratory
  boarding/alighting reconstructions are conditional on matching and run
  assignment. The unavailable crowding response is intentional.
- The supplied Delhi GTFS ZIP matches the committed import digest. A real
  imported database provided baseline readiness and browser data.
- Docker Compose uses FastAPI and Caddy with a persistent database and a
  non-root backend. The Python image installs test dependencies and unpinned
  version ranges. Root health endpoints, consistent request diagnostics,
  repeatable first-run commands and CI are missing.
- Stops autocomplete is bounded in the browser, but list endpoints lack page
  offsets and some searches have no query length constraint. The initial
  stop catalog is needed by itinerary labels and remains a large response.
  Timetable analytics are cached, with a potentially expensive cold request.
- The repository scan found no production TODO/FIXME stubs in the runtime.
  Localhost values are development and container defaults. Playwright uses
  browser interception for deliberate failure scenarios. The demo CSV is
  actual historical aggregate data, rather than a simulator.
- Root pytest in the ML directory collects a Parquet diagnostic under
  `src/` that depends on unavailable upstream material. The test directory
  contains the self-contained automated suite. Previous reports mix
  pre-integration and integrated results.
- Queries use bound parameters. Public API errors hide server details, but
  trace logging and request IDs are inconsistent. Hardening should focus on
  request limits, protected data mounts, runtime dependencies, and safe
  handling of optional credentials.
- Full-network integration is constrained by an adapter hardcoded to the
  demo export filename and crosswalk. A more flexible configuration can
  accept independently validated artifacts while preserving demo behavior.

Priorities and external dependencies are tracked in
[the issue register](FINAL_ISSUE_REGISTER.md). Preserve the supplied
predictor, journey behavior and UI while adding validation, status and
reproducible verification.


## Review after implementation

The revised runtime preserved the baseline planner and historical lookup. It
added configurable artifact validation, public coverage and route-day
profiles, mobile demand analytics, root probes, bounded concurrency, request
correlation, narrower container dependencies and an optional authorized
GTFS-Realtime provider. The reproducible checks use the supplied archive and
original integrated data. Remaining limits stem from the unavailable
full-network export, unverified vehicle-occupancy ground truth, live feed
authorization, infrastructure and the first expensive analytics query.
[Current project status](FINAL_PROJECT_STATUS.md)
