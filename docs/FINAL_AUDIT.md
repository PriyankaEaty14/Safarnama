# End-to-end SAFARNAMA audit

Reviewed 24 November 2026 against GitHub baseline `d7ca5e1`, the
user-described Windows behavior, and the supplied Delhi GTFS database in a
read-only Docker mount. The planner, explorer, analytics, import and Member 1
artifacts remain in the existing repository.

| Issue | Severity | Finding and correction |
|---|---|---|
| JP-01 | P0 | Old uniqueness used trip IDs. Equivalent trip records can duplicate a result. Real examples combining 73UP and 85EXTUP also hid distinct transfers on collapsed cards. The planner now deduplicates equivalent paths before limiting, and the UI identifies the actual transfer. |
| JP-02 | P0 | The planner previously used the entered hour even after that hour had passed. The API now enforces the Delhi clock for same-day trips. Past dates require explicit historical lookup. |
| JP-03 | P1 | A generic transfer fallback could permit a connection across stops without a published minimum. Cross-stop transfers now require adequate timing evidence in GTFS. |
| ML-03 | P1 | Routes in the reported search are absent from the verified directional crosswalk, and different artifact failures previously looked alike. API reason codes and UI explanations now distinguish these cases. |
| UX-03 | P1 | Empty segment controls and repeated prediction labels implied that something was missing from the display. Crowd indicators now require validated categories. |
| UX-04 | P2 | Collapsed cards hid the transfer stop, second boarding, and wait. Cards and the route explorer now make the transfer sequence clear. |
| UX-05 | P2 | Background tile failures were silent. The explorer describes the failure and keeps the GTFS route overlays and markers. |
| PERF-03 | P2 | Repeated linear stop-name lookups were unnecessary. The planner now builds a stop-name index once per loaded catalog and the backend reuses stop sequence slices within each search. |

[Issue register and evidence](FINAL_ISSUE_REGISTER.md)

The analytics service applies the same GTFS date rules as the planner to
a seven-day published sample. The covered example week includes weekdays
and weekend dates. Traffic capacity and multi-instance deployment still
require staging validation.
