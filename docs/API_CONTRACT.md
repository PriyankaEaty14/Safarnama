# Safarnama API v1

All requests use HTTP GET. The base path is `/api/v1`. Dates use
`YYYY-MM-DD`; departure times use `HH:MM` in Asia/Kolkata. IDs are GTFS
strings, including numeric-looking IDs. URL-encode IDs and query values.
Interactive documentation is at `/docs`, and the typed OpenAPI document is at
`/openapi.json`.

| Path | Query parameters | Example request | Success response and endpoint errors |
|---|---|---|---|
| `/health` | None | `GET /api/v1/health` | `{"status":"ok","database":"ok"}` or 503 with `status:"degraded", database:"unavailable"` |
| `/ready` | None | `GET /api/v1/ready` | `{"status":"ok","database":"ok","schedules":"ready"}` or 503 with `schedules:"missing"` or `"unknown"` |
| `/stops` | Optional name substring `q` and integer `limit` (default 100, 1–10,000) | `GET /api/v1/stops?q=Rohini&limit=5` | Array of Stop objects, empty when unmatched |
| `/stops/{stop_id}` | None | `GET /api/v1/stops/1` | Stop object or 404 |
| `/routes` | Optional name substring `q` and integer `limit` (default 100, 1–3,000) | `GET /api/v1/routes?q=102ADOWN&limit=5` | Array of Route objects, empty when unmatched |
| `/routes/{route_id}` | None | `GET /api/v1/routes/1` | Route object or 404 |
| `/routes/{route_id}/trips` | Optional integer `limit` (default 100, 1–1,000) | `GET /api/v1/routes/1/trips?limit=1` | Array of Trip objects, or 404 for an unknown route |
| `/routes/{route_id}/stops` | None | `GET /api/v1/routes/1/stops` | Array of distinct Stop objects, or 404 for an unknown route. Sorted by name. Use journey legs for trip ordering. |
| `/routes/{route_id}/geometry` | Optional `trip_id`. For a segment, also send nonnegative integers `from_stop_sequence` and `to_stop_sequence`. Legacy `from_stop_id` and `to_stop_id` alone do not resolve repeat occurrences. | `GET /api/v1/routes/1/geometry?trip_id=1_FULL_08_35&from_stop_sequence=0&to_stop_sequence=10` | Geometry object. 404 for an unknown route or trip, 422 for incomplete or reversed sequence queries. |
| `/journeys` | Required `origin`, `destination`, `date`, `time`. Optional `preference` and integer `limit` (default 12, 1–30). | `GET /api/v1/journeys?origin=1&destination=7547&date=2026-11-23&time=08:35&limit=1` | Array of Journey objects, empty when no schedule qualifies. 404 for unknown stops or 422 for invalid inputs. |
| `/crowding` | No context for a general status. Provide `journey_id,date` with optional `time`, or `route_id,from_stop_id,to_stop_id,date,time` with optional `direction`. | `GET /api/v1/crowding?route_id=2171&from_stop_id=2640&to_stop_id=3250&date=2026-11-27&time=08:35` | Validates GTFS route, stop order, service date and direction. Returns the current unavailable prediction and optional resolved leg metadata. |
| `/demand/historical` | `route_id,date,time` | `GET /api/v1/demand/historical?route_id=2171&date=2026-11-27&time=08:35` | Historical route-hour estimate and provenance. Invalid date/time is 422 and unknown GTFS route is 404. Unsupported routes or data return explicit status and a null estimate. |
| `/analytics` | None | `GET /api/v1/analytics` | Analytics object. Counts are zero and schedule series empty for an empty database. |

Unrecognized paths and missing entities return 404 with
`{"detail":"Stop not found"}` or the relevant message. Invalid typed
parameters return 422 with a `detail` array describing field errors.
Business-rule violations can return 422 with a string `detail`. Database
failures return 503 with a generic message, and unexpected failures return
500 with `{"detail":"Internal server error"}`.

## Stop, Route and Trip

Stop has string `id` and `name`, numeric `lat` and `lng`, and nullable
string `code`. Example:

```json
{"id":"1","name":"Rohini Sec 22 Terminal","lat":28.71797103184126,"lng":77.06389993096785,"code":"9CE15308"}
```

Route has string `id` and `agencyId`, and nullable string `shortName`,
`longName` and `description`. Example:

```json
{"id":"1","shortName":"102ADOWN","longName":"102ADOWN","description":"Rohini Sec 22 Terminal to Azadpur Terminal","agencyId":"DIMTS"}
```

Trip has string `id` and `serviceId`, and nullable string `headsign`,
`directionId` and `shapeId`. Example:

```json
{"id":"1_FULL_06_05","serviceId":"1","headsign":"Azadpur Terminal","directionId":null,"shapeId":"shp_3_2800"}
```

List responses wrap the corresponding objects in a JSON array.

## Geometry

`status` is `available` or `unavailable`. `coordinates` is an ordered array
of numeric `[latitude, longitude]` pairs, empty when unavailable. `reason` and
`shapeId` are nullable strings. Without `trip_id`, the API returns a
representative shape for a known route when available. Segment geometry
aligns stops in trip order to the published shape. For example:

```json
{"status":"unavailable","reason":"No shape is published","coordinates":[],"shapeId":null}
```

## Journey

All displayed times are integer minutes from midnight of the requested city
date. Intermediate stop times can be negative or beyond 1,440. Exact seconds
are used to check catchability and the inclusive six-hour cutoff for every
boarding. Arrivals can fall after the cutoff. Direct and one-transfer
journeys are searched. Same-stop changes default to 3–60 minutes. Published
stop-level type 2 transfers use the feed minimum and extend the wait window
if necessary, within the six-hour cutoff. Type 3 prohibits the connection.
Cross-stop changes require a published transfer.

`fastest` orders by arrival, then transfer count and departure. `balanced`
adds a ten-minute transfer penalty to the sort score. The legacy
`comfortable` key still uses the fastest schedule ordering. No schedule
preference claims crowd optimization. IDs encode the ordered leg
occurrences and remain opaque to clients.

| Journey field | Type and meaning |
|---|---|
| `id` | String |
| `departure`, `arrival`, `duration` | Integers in minutes |
| `transfers`, `transferDuration` | Integers. Total transfer time includes walking for a cross-stop change. |
| `legs` | Array of one or two Leg objects |
| `coverage` | Number. Zero segments have a validated estimate today. |
| `busiest`, `confidence` | Nullable Segment and number respectively |
| `crowdingStatus`, `rankingStatus` | Strings. `unavailable` and either `schedule_only` or `schedule_based`. |

Each Leg has strings `tripId`, `routeId`, `route`; integers
`boardSequence`, `alightSequence`, `start`, `end`; nullable string
`direction`; and ordered `stopIds`, `stopTimes` and `segments` arrays.
Each stop time is `{"arrival":int|null,"departure":int|null}`, paired by
index with its stop ID. Each Segment has string `from`, string `to` and
nullable string `level`. A compact example:

```json
[{"id":"[[\"T\",0,\"A\",1,\"B\",515]]","departure":515,"arrival":529,"duration":14,
  "transfers":0,"transferDuration":0,"legs":[{"tripId":"T","routeId":"R","route":"R",
  "boardSequence":0,"alightSequence":1,"direction":null,"stopIds":["A","B"],
  "stopTimes":[{"arrival":515,"departure":515},{"arrival":529,"departure":529}],
  "start":515,"end":529,"segments":[{"from":"A","to":"B","level":null}]}],
  "coverage":0,"busiest":null,"confidence":null,"crowdingStatus":"unavailable","rankingStatus":"schedule_only"}]
```

## Crowding

A request without context returns the general unavailable status. Supply the
planner's opaque `journey_id` and original search date to resolve up to two
GTFS legs. Supply the original search time when available to validate that the
legs fall within the six-hour boarding window. For a direct segment query,
supply the GTFS route, two stop IDs, service date and local time. Direction can
be GTFS `0` or `1`, or directional route code suffix `UP` or `DOWN` where
present. The direct date identifies the GTFS service day. Journey dates
identify the search date, then each leg's service day is resolved from the
trip calendar and extended-hour stop times.

Unknown route, stop or scheduled leg returns 404. Mixed or incomplete
parameters, invalid time, inactive service or incompatible stop ordering
return 422. Valid context adds `legs` to the original response contract.
`segments` remains empty because no segment prediction is supplied.

```json
{"status":"unavailable","source":null,"historical":false,"estimatedPassengerLoad":null,
 "category":null,"confidence":null,"capacity":null,"modelVersion":null,"timeWindow":null,
 "segments":[],"legs":[{"legIndex":0,"routeId":"2171","direction":"UP",
 "fromStopId":"2640","toStopId":"3250","serviceDate":"2026-11-27","minuteOfDay":515,
 "status":"unavailable"}],"reason":"Validated trip-segment occupancy predictions are not available."}
```

## Historical demand

This endpoint uses the requested Delhi civil date and hour. Weekdays run from
Monday zero through Sunday six. Any applicable date selects a recurring
weekday/hour pattern from the October 2026 export. The lookup does not
generate a date-specific forecast. UI queries use each leg's scheduled boarding
hour, including the date rollover after midnight.

```json
{"status":"historical_estimate","route_id":"2171","route":"717AUP","day_of_week":4,
 "hour":8,"applicable_hour_start":"2026-11-27T08:00:00+05:30","timezone":"Asia/Kolkata",
 "metric":"historical_ticketed_passengers_per_route_hour","unit":"ticketed_passengers_per_route_hour",
 "label":"Historical estimated ticket demand","estimated_ticketed_passengers":82.6,
 "historical_daily_std":27.68,"historical_calendar_days":5,
 "source":"October_2026_ETM_historical_baseline","model":"route_weekday_hour_mean","schema_version":"1.0",
 "training_period":{"start":"2026-10-01","end":"2026-10-31"},"is_live":false,
 "is_actual_occupancy":false,"reason":null}
```

A genuine zero remains numeric zero. `unsupported_route` means the known
GTFS route has no verified mapping in this export. `insufficient_data` means
the mapped route has no value for the requested weekday/hour. `unavailable`
covers missing artifacts, mapping errors, and rejected responses. These
statuses carry an explicit reason and a null estimate. Historical standard
deviation measures variability across observed calendar days, some of which
include zero-filled no-transaction hours. The export has no calibrated
confidence score, current passenger loads or seat counts.

## Analytics

`counts` has integer `agencies`, `stops`, `routes`, `trips`, and
`stopTimes`. `serviceDates.first` and `serviceDates.last` are nullable
published calendar bounds. Each `scheduledDeparturesByHour` entry has
integer `hour` and `trips`. Each scheduled trip with a departure contributes
once at its first departure. GTFS hours above 23 retain their service-day
offset. Each of up to 10 directional `corridors` has string `fromStopId`,
`fromStopName`, `toStopId`, `toStopName`, and integer
`scheduledTraversals` and `distinctRoutes`. A traversal is one occurrence of
consecutive different stops in the timetable. These aggregates describe
schedule records across the feed. Historical passenger metrics remain
unavailable. The example below abbreviates the schedule arrays.

```json
{"counts":{"agencies":2,"stops":6862,"routes":2574,"trips":80357,"stopTimes":2737136},
 "serviceDates":{"first":"2025-01-01","last":"2040-01-01"},
 "scheduledDeparturesByHour":[{"hour":15,"trips":5344}],
 "corridors":[{"fromStopId":"7571","fromStopName":"GGS University ISBT Kashmere Gate",
 "toStopId":"117","toStopName":"GPO Kasmeri Gate","scheduledTraversals":2971,"distinctRoutes":93}],
 "historicalRecords":{"status":"unavailable","value":null},
 "hourlyDemand":{"status":"unavailable","values":[]},"routeDemand":{"status":"unavailable","values":[]},
 "peakHours":{"status":"unavailable","values":[]},"weekdayWeekend":{"status":"unavailable","values":[]},
 "crowdingDistribution":{"status":"unavailable","values":[]}}
```

## Readiness, pagination and request metadata

- `GET /health` checks process liveness. `GET /ready` checks database
  connectivity and imported schedules and returns 503 when they are missing.
  Existing `/api/v1/health` and `/api/v1/ready` remain available.
- Successful and failed application responses carry a generated `X-Request-ID`.
  Query strings over 4,096 bytes return HTTP 414. Saturated journey searches
  return HTTP 429 and a `Retry-After` header.
- The stops and routes lists accept an optional zero-based `offset` and
  preserve stable ordering.

## Historical coverage and profiles

`GET /api/v1/demand/coverage?limit=100&offset=0` gives the exported row count,
missing buckets, artifact SHA-256, mapped and imported route counts, and a
page of verified directional mappings. Results distinguish a missing artifact
from routes outside coverage. `GET /api/v1/demand/profile?route_id=2171&date=2026-11-27`
returns one record per Delhi hour using the existing historical demand
response type. An unsupported route has null demand values. Unknown GTFS route
IDs return HTTP 404. Both endpoints work with the demo crosswalk and with an
operator-supplied reviewed crosswalk.

## Optional live vehicle positions

`GET /api/v1/live/vehicles?limit=100` reports `disabled`, `unavailable`,
`stale` or `available`. Optional fields include the feed observation
timestamp, valid vehicle count and up to 500 positions from the authorized
Delhi provider. Each record contains position, observation time and optional
provider route ID. Provider IDs are presented as supplied, without a
schedule crosswalk. Responses use `Cache-Control: no-store`.
[Provider and credentials](DEPLOYMENT_GUIDE.md)

## Journey search time and identity

`mode=upcoming` is the default. For the current Delhi date, the API clamps
the earliest boarding to the server’s current time. For a future date, it
uses the requested time. An earlier Delhi date returns 422 unless
`mode=historical` is supplied. That mode is a timetable lookup.

`itineraryId` identifies the ordered stops, route IDs and exact times of
the journey. The original `id` still resolves the representative GTFS
trip IDs and stop sequences. Leg fields `departureSeconds` and
`arrivalSeconds` are relative to the search date at Delhi midnight, alongside
the existing minute fields. `transferMinimumSeconds` carries a valid
cross-stop GTFS minimum when present.

Historical demand includes `direction` for verified UP/DOWN routes and
`reason_code` for insufficient, unsupported or unavailable results.

Network analytics also exposes `scheduledServiceWeek`, the first seven
published calendar dates (fewer for a shorter feed) with scheduled trip
counts and a weekend flag. It uses GTFS service activation and exceptions.
