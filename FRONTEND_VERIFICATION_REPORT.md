# Frontend verification report

This document records an earlier project milestone. See the [current verification and status](docs/FINAL_TEST_REPORT.md) for the latest evidence.

This archive records the pre-update state. See the [current testing report](docs/TESTING_REPORT.md).

`npm run build` passed on 23 November 2026. Vite warned that the main JavaScript
chunk exceeds 500 kB, and displayed two non-fatal React Router `use client`
directive warnings. No lint or type-check script is configured in
`package.json`.

The targeted pass repeated `npm run build` successfully after changing the
preference and comparison text. The "Less crowded" option now discloses the
schedule-only fallback in the form before search. The comparison panel states
that crowding comparison is unavailable. Editing a search input clears prior
results so they are not presented for a changed query.

The existing React interface was tested in the browser with FastAPI on port
8765 and Vite on port 5173. The workflow loaded the initial form, selected
Anand Vihar ISBT and Shivaji Stadium Terminal from real stop search, set
08:35, searched, and displayed scheduled journeys. The selected journey showed
the Karkardooma transfer, ordered stop details, an explicit unavailable
crowding state, and map lines for both journey legs. The inspected map had
two route polylines and 21 markers. The analytics screen showed the imported
2 agencies, 6,862 stops, 2,574 routes and 80,357 trips. Clearing a stop
produced an invalid-input message. Stopping FastAPI produced an analytics
error with a retry action; restarting it and retrying restored the metrics.

The targeted browser check used the updated backend and frontend on ports 8766
and 5174. It showed the preference warning before search; searched from Anand
Vihar ISBT to Shivaji Stadium Terminal (Connaught Place) at 08:00 on 23
November 2026; displayed 12 journey options and an explicit unavailable
crowding comparison; expanded the first transfer journey at Karkardooma
Crossing; and displayed its selected two-leg map with 2 route polylines and
21 markers. Analytics showed 2 agencies, 6,862 stops, 2,574 routes and
80,357 trips. Clearing the destination produced the invalid-input alert.
After stopping the backend, analytics displayed an error and a retry button;
restarting the backend and clicking retry restored the counts. After the final
search-state edit, a new journey search returned 12 options, and editing the
destination cleared those results. Map tile availability depends on internet
access. No automated browser test suite is configured.
