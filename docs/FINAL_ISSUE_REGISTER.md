# SAFARNAMA issue register

| ID | Priority | Area | Problem and impact | Correction | Status | Verification |
|---|---|---|---|---|---|---|
| SEC-01 | P1 | API / Caddy | Oversized inputs and opaque errors complicate public operation. | Bound request inputs, correlate errors and logs, configure proxy timeouts. | Implemented | API regressions and local probes |
| ML-01 | P1 | Historical demand | Demo-specific artifact configuration and missing full-network export limit coverage. | Support explicit artifact/crosswalk configuration and report available coverage. | Implementation verified for demo. Full export external | Actual backend coverage and CSV parity |
| ML-02 | P1 | Occupancy | No verified per-bus ground truth or capacities. | Keep provider contract and document data requirements. | External | Validate unavailable and null fields |
| LIVE-01 | P1 | Feed | Delhi vehicle positions require authorized access. | Add a disabled-by-default provider and expose freshness/status. | Provider implemented. Credentials external | Confirm disabled response and credential handling |
| DATA-01 | P1 | Setup | Developer setup, feed validation and import are separate manual steps. | Add reproducible commands with safe initialization. | Data validator verified. Fresh import not repeated | Supplied ZIP digest and read-only data checks |
| API-01 | P1 | Readiness | Only versioned probes and an incomplete readiness signal are exposed. | Preserve legacy probes and expose root probes. | Implemented | Empty and loaded database tests |
| CI-01 | P1 | Deployment | No workflow covers tests and builds. | Add CI on pull requests and main. | Workflow defined. Hosted run pending | Local verification script passed |
| UI-01 | P2 | Analytics | The schedule UI does not surface available historical route coverage. | Add bounded catalog and route/weekday historical chart. | Implemented | Real-data Chromium test at 360px |
| UI-02 | P2 | Frontend | A render error can blank a full view. | Add route content error boundary. | Implemented | Frontend build and browser suite |
| PERF-01 | P2 | Performance | Cold schedule analytics, catalog size and startup need measurement. | Profile current and final application under the same workload. | Measured. Cold analytics remains slow | Timed loopback and 12-request burst |
| DEV-01 | P2 | ML tests | Default collection attempts to run a data-dependent diagnostic. | Classify automated tests and document explicit diagnostic prerequisites. | Implemented | 43 tests with bare pytest from ml |
| DOC-01 | P2 | Documentation | Historical reports can be mistaken for current evidence. | Add dates/status and current data, tests and deployment references. | Updated | Review status, baseline and final evidence |
| PERF-02 | P3 | Planning | Extra transfers require a new algorithm and performance validation. | Preserve validated direct and one-transfer paths. | Deferred | Existing journey tests |

## End-to-end journey review

| Issue | Severity | Affected code | Implemented and verified | Remaining limitation |
|---|---|---|---|---|
| JP-01 | P0 | Journey service, React planner | Route, ordered stops and exact seconds define equivalent itineraries. GTFS fixture covers different trip IDs, and Chromium covers duplicate cards. | True alternate transfer paths may share route labels. |
| JP-02 | P0 | Journey API, app clock, search form | Delhi current-time cutoff and explicit historical mode. Clock tests cover second precision, future dates and an overnight arrival window. | Schedule departure estimates depend on the supplied GTFS feed. |
| JP-03 | P1 | Journey service, transfer display | Explicit positive minimum for changes across distinct stops, same-stop buffers, and a 60-minute maximum connection. Tests cover missing and supported minima. | The supplied feed has no explicit walking links. |
| ML-03 | P1 | Historical adapter, API and details | Safe reason codes, verified direction and complete demand display. Test coverage includes unsupported routes, missing files, checksum failure and invalid mapping. | Export still covers 20 of 2,574 routes. |
| UX-03 | P1 | Planner and itinerary | Removed blank strip and per-stop crowding markers when evidence is unavailable. Chromium checks both available demand and unavailable crowding. | Validated occupancy observations remain external. |
| UX-04 | P2 | Planner and explorer | Cards surface the real transfer stop, second boarding and wait, with the full itinerary and map available. | Walking distance is unavailable in the data. |
| UX-05 | P2 | Route explorer | Tile failures produce an explanatory message and retain GTFS overlays. | The basemap depends on its external provider. |
