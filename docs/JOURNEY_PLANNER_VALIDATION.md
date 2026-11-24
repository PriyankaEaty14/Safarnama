# Journey planner validation

## Identity and sorting

Each result has an `itineraryId` derived from ordered leg route IDs, exact
departure and arrival seconds, and the full ordered stop IDs per leg. The
existing `id` continues to encode the representative GTFS trip and stop
sequences for crowding and map lookup. Equal schedules on different trip IDs
collapse before the result limit. The route explorer still opens a real
representative trip. Different boarding times, paths and transfer points
remain available. Deterministic ordering uses scheduled arrival, transfers
and departure, followed by itinerary identity. Balanced ranking applies a
10-minute penalty per transfer. The search supports direct and one-transfer
journeys.

The 24 November 2026 timetable at 09:30 for Anand Vihar ISBT to West Enclave /
Sansad Vihar produced 30 distinct results at limit 30. Several begin with
73UP and 85EXTUP at the same departure. Some change at Rainy Well, Delhi
Secretariat or ITO AGCR / ITO. The revised cards identify these connections
individually. An automated GTFS fixture proves that exact duplicate trip
records collapse while a distinct one-second departure survives.

## Service date and time

Normal searches use Delhi local time. A same-day request starts at the later
of the selected time and the server clock, rounded forward to the next whole
second where necessary. A future date uses the entered time. To inspect a
past timetable, select historical lookup in the UI or send
`mode=historical` to `GET /api/v1/journeys`. The UI labels these results
as historical. Times past midnight may draw from a previous GTFS service
date. The planner checks weekday calendars and date exceptions for each run.
The supplied data declares Monday through Sunday service from January 2025
through January 2040. That range describes the archive’s validity.

## Transfers

For the supplied archive, zero transfer records means the planner can use
the same physical GTFS stop ID with a three-minute minimum buffer. It
accepts stops that differ only with an explicit positive GTFS type 2
connection minimum. Type 3 prohibitions are enforced. Timed same-stop
connections can meet at the same timestamp. The maximum elapsed transfer
time is one hour. Walking distances, pedestrian accessibility and
real-world connection guarantees are unavailable in the supplied feed.

Tests cover direct and transfer ordering, calendar overrides, invalid and
overlong connections, cross-stop minimums, overnight times, timezone
rollover, same-day filtering and equivalent trips. Browser scenarios
exercise a real transfer, route geometry and unique rendering, including an
intentional duplicate inserted into a successful real API response.
[Verification commands and outcomes](FINAL_TEST_REPORT.md)

A real same-day request for 09:30 sent at 15:53:44 IST returned 15:55 as
the earliest boarding. The explicitly historical request for the same
recorded timetable still returned the 09:30 departure.
