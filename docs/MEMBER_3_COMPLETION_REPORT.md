# Member 3 frontend completion

This document records an earlier project milestone. See the [current verification and status](FINAL_TEST_REPORT.md) for the latest evidence.

The baseline supplied the React layout, branding, planner, Leaflet explorer
and data-connected summary cards. The updated app uses that integrated frontend
as its base.

## Delivered

- The planner uses the Stops and Journeys APIs with corrected stop selection,
  keyboard suggestion controls, clear loading and retry states, and the
  schedule-supported Fastest and Balanced preferences.
- Journey cards show scheduled departure and arrival, duration, boarding and
  alighting stops, and interchange timing. Expanded cards fetch the
  Crowding API availability message.
- The explorer fetches GTFS geometry for each leg. It draws validated route
  points, positions endpoints/interchanges and maps valid stops when geometry
  is unavailable. Lazy loading keeps Leaflet out of the initial planner bundle.
- The network dashboard uses the API for counts, an hourly schedule chart and
  directional corridor statistics. The chart component loads on demand.
- The Playwright suite exercises the production frontend against Delhi GTFS,
  including error and empty-state controls and narrower layouts.

Map tiles come from OpenStreetMap. Journey overlays use the GTFS geometry API
and remain available if the tile provider cannot be reached. See the
[testing report](TESTING_REPORT.md) for the verified desktop, tablet and
mobile scenarios.
