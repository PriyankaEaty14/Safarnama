# Member 1 integration handoff

The backend uses the original `ml/src/safarnama_predictor.py` and
`ml/src/demand_lookup.py`, the 20-route demo export, its manifest, and the
provided JSON Schema. Startup validates the manifest, artifact hash, row and
route counts, numeric fields and the explicit GTFS crosswalk. Lookup validates
the returned schema and provenance before the historical endpoint projects
display fields. The integrated GTFS import identifies the feed by SHA-256.
The crosswalk was checked against that feed and is validated against installed
routes at startup, including agency identity and unique exact directional
labels in the GTFS short and long name fields.

The archived CSV has SHA-256
`16841fff58fc44447f9a66e26242af08460ea87a3c3fa86fdd96227d68a0cf14`.
Restoring CRLF line endings in memory exactly reproduces the supplied export
manifest digest `a2a8d33e9c75ef983af643cb7f3173284f888bb1897aa3f7bc9d83207472e50e`.
The adapter accepts that proven newline conversion and leaves the archive
bytes unchanged. Other checksum mismatches disable historical demand.

`GET /api/v1/demand/historical` exposes ticketed passengers per route-hour
aggregated over trips. The trained calendar covers October 1–31, 2026, and
the estimate is a weekday/hour mean. Standard deviation describes historical
variation. The analysis reports 29.52% WAPE on the top-20 holdout used in
model selection. The full 354,816-row export and source ETM data are absent.

Future segment-level crowding support needs a ground-truthed per-bus load
artifact with verified trip identity, ordered stops, time interval, calibrated
uncertainty where available, and vehicle capacity evidence before seating can
be inferred. The existing `SegmentKey` / `MLAdapter` seam handles validated
request context. Its active provider remains the unavailable adapter.

See [the Member 1 handoff](../ml/outputs/SAFARNAMA_BACKEND_HANDOFF.md) and
[API contract](API_CONTRACT.md).
