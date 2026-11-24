# Work dependent on Member 1

This document records an earlier project milestone. See the [current verification and status](FINAL_TEST_REPORT.md) for the latest evidence.

| Blocked work | Member 1 handoff | Member 2 follow-up | Member 3 follow-up | Verification |
|---|---|---|---|---|
| Trip and segment prediction lookup | Versioned inference output, GTFS join keys, time semantics and sample records | Implement and validate the provider adapter, including ambiguous and missing keys | Render supported segment values and partial results | GTFS ID and sequence parity, midnight cases and real prediction fixtures |
| Passenger load, seat categories and confidence | Target/units, capacity provenance, category thresholds and calibrated confidence where available | Validate ranges and availability and expose agreed fields | Display only supported measures with provenance | Compare UI values with reference records and check unavailable/error states |
| Crowding-aware ranking | Coverage per leg, validated ranking targets and evidence that alternatives are comparable | Implement ranking with explicit fallback, tie and coverage rules | Expose the preference once supported and describe the selected ranking | Compare ranked alternatives against held-out journeys, including partial coverage |
