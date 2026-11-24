# Known issues and dependencies

This document records an earlier project milestone. See the [current verification and status](docs/FINAL_ISSUE_REGISTER.md) for the latest evidence.

This archive records the pre-update state. See the [current testing report](docs/TESTING_REPORT.md).

- No validated trip-segment occupancy, vehicle capacity, or confidence output
  was supplied. Crowding remains explicitly unavailable. Historical
  route-hour ticket demand cannot support seats or live occupancy.
- The archived source omits the 330 MB generated SQLite database and 29 MB
  original GTFS ZIP. Reimport the identified feed to run schedule searches.
- Trip `direction_id` is blank throughout the supplied feed, so the API
  cannot expose an authoritative direction value for those trips.
- Geometry alignment uses ordered stops and a distance tolerance. Trips with
  missing or ambiguous shape alignment return unavailable; no route is drawn
  from fabricated points.
- Journey search requires every boarding, including the transfer bus, to
  depart within six hours of the requested time (boundary inclusive). Arrival
  may occur later. It supports direct or one-transfer travel; longer
  itineraries and later boardings are outside the API scope.
  A representative real-feed transfer search took about 4.7 seconds locally;
  high-traffic performance has not been load tested.
- The main frontend bundle is about 516 kB and triggers Vite's size warning.
  There is no configured frontend lint, type-check, or automated browser suite.
- OpenStreetMap tiles and external fonts require internet access.


## Integration update

Historical route-hour demand is available for 20 explicitly mapped routes.
The archive omits full-network prediction exports and original ETM data.
Live and segment-level occupancy, capacity, and crowding-aware ranking
remain unavailable. See the [integration report](docs/INTEGRATION_REPORT.md)
for the current state.
