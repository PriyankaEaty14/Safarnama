# Safarnama verification, 24 November 2026

| Check | Result |
|---|---|
| Original backend baseline | 15 passed |
| Updated backend, `python -m pytest -q` | 20 passed |
| Production frontend, `npm run build` | Passed. 354.06 kB main JS, with separate explorer and analytics chunks |
| Browser suite against Docker Compose | 6 passed in 33.7 seconds |
| Dependency checks | `pip check` found no broken requirements and `npm audit --omit=dev` reported zero known vulnerabilities at run time |
| Container deployment | Both images built. Real feed import ran in the non-root backend container. Local Caddy origin served the app, SPA fallback, readiness and 12 OpenAPI paths. |
| SQLite integrity | `PRAGMA integrity_check` returned `ok`. `foreign_key_check` returned no rows. The stop-and-departure and trip/sequence indexes were present. |

The automated browser checks used Chromium with the built React app, Caddy,
FastAPI and the imported Delhi database. They verified keyboard and mouse stop
selection, input validation, the direct and two-leg transfer paths, geometry,
analytics, unavailable crowding, loading, empty and retry states, and
390 px mobile and 820 px tablet widths. The successful transfer and analytics
test checked for uncaught browser errors and failed application API responses.
Tests simulated errors and invalid geometry only in the relevant negative
cases. Tests isolated external fonts and basemap tiles; the map shapes still
came from the real API. An OpenStreetMap test tile returned HTTP 200 in a
separate HTTP check.

## Real-feed evidence

- The archived input `delhi_buses_static_gtfs_v1.zip` was imported in the
  local Python environment and again through the Compose import command.
  Both updated imports recorded 2 agencies, 6,862 stops, 2,574 routes,
  80,357 trips, 2,737,136 stop times and 965,607 shape points, with zero
  rejected or duplicate rows. The database has 18,457 departures at
  GTFS hours 24 or later. The committed report records the input checksum.
- On 23 November 2026 at 08:35 IST, stop `1` to `7547` returned 12
  distinct options. The first was a direct 08:35–08:49 trip with 46
  published geometry points.
- The same date and time from `917` to `365` returned 12 distinct options.
  The first used a transfer, departing 08:40 and arriving 09:22. Its two
  leg geometries returned 43 and 152 points.
- In one HTTP smoke run through Caddy, the direct and transfer searches
  took 0.286 and 0.798 seconds, respectively. The first analytics request
  took 6.499 seconds and the cached repeat took 0.008 seconds. These are
  local observations. Concurrent production load remains unmeasured.
- Analytics summed 80,357 first departures and returned 10 directional
  corridors. The crowding response reported unavailable and gave no
  estimated passenger load.
- The supplied feed has neither `calendar_dates.txt` nor `transfers.txt`.
  Fixtures cover calendar additions/removals, explicit cross-stop and
  prohibited transfers, loop geometry, missing geometry, and the inclusive
  cutoff for both boardings.

The final suites had no failures. Starlette emitted an HTTPX test-client
deprecation warning. Vite emitted two non-fatal React Router directive
warnings. An earlier browser run surfaced a Leaflet cleanup error when
leaving the map during an automatic zoom. The fix passed the full rerun.

## Remaining external dependencies

Crowding prediction integration awaits the Member 1 handoff. The October CSV
exceeded the workspace transfer limit and was outside the schedule workflow.
Public HTTPS awaits a target host and DNS access. The tested environment
provided a local containerized app; it did not provide a public hosting target.
