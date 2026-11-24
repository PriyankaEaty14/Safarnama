# Members 2 and 3 initial audit

The full-stack archive is the source baseline. The other archive contains the same assets and styling but a frontend-only implementation with demo data. Its shipped demo paths are unsuitable for the integrated application.

| Area | Existing implementation | Gaps found in review |
|---|---|---|
| Backend | FastAPI entry point in `backend/app/main.py`, versioned routers, typed journey response, SQLAlchemy and SQLite | Some successful and error responses lack OpenAPI detail. Database failure on the health route returns HTTP 200. CORS coverage on unhandled errors needs verification. |
| GTFS | Streaming CSV processing into a staged SQLite file, relationship checks, calendar exceptions and validation report | Ignores transfers and agency timezone requirements, leaves failure diagnostics incomplete, and does not catch chronology regressions across partial stop times. |
| Journey planning | Direct and same-stop one-transfer searches, date exceptions, inclusive six-hour boarding window, ordered-leg deduplication, and balanced ranking | Repeats destination queries for overlapping transfer windows and expands full legs before ranking. Drops direction metadata and looks back just one GTFS service day. |
| Geometry | Shape alignment by ordered trip stop sequence | Route-level geometry returns 404 for a known route without a shape. The explorer can draw an inferred straight segment and assumes geometry coordinates are valid. |
| Analytics | Database counts for agencies, stops, routes and trips | No schedule hourly distribution or corridor statistics. Historical demand fields are unavailable. |
| Frontend | React 19 and Vite, hash navigation, Axios, Leaflet, planner, map and analytics | Stop input can show stale names after swapping a blank field. Suggestions show empty before the request finishes. Less crowded appears selectable although only a schedule fallback exists. No executable frontend suite. |
| Deployment | Environment examples and local commands | No production packaging or repeatable deployment configuration. SQLite import and runtime path can diverge. |
| Crowding | Explicit unavailable adapter and UI | Member 1 must supply versioned, validated predictions and GTFS mapping before crowd rankings, estimates or confidence can be enabled. |

The supplied Delhi GTFS archive contains agencies, stops, routes, trips, stop times, a calendar, shapes and feed metadata. Calendar exceptions and transfers are absent from this feed. The October CSV exceeded the executor transfer limit and is outside the schedule-based validation.

Baseline executable checks before project changes confirmed 15 backend tests
passing and a successful Vite build. The main JavaScript chunk was 515.73 kB.
The baseline importer successfully loaded the supplied Delhi ZIP. The
validation issues above were found by reviewing the implementation and
exercising edge cases separately from the original test suite.
