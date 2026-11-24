# Historical demand coverage report

Verified with the supplied Delhi static GTFS feed and original Member 1
demo artifact on 24 November 2026.

| Measure | Result |
|---|---:|
| Imported directional GTFS routes | 2,574 |
| Verified mapped routes | 20 |
| Routes in the historical export | 20 |
| Unique route-weekday-hour prediction rows | 3,360 |
| Imported routes without verified predictions | 2,554 |
| Missing weekday-hour keys in the demo export | 0 |

The browser and API resolve directional GTFS route IDs using the versioned
crosswalk. Example routes 73UP (2206), 85EXTUP (2342) and 85UP (2343) have
no verified directional mapping in this export. This explains unavailable
estimates in the reported transfer results. The 717AUP route (2171) returns
82.6 estimated ticketed passengers at Friday 08:00 IST, verified against
the original CSV. Direction, source, schema version, historical variability
and observed days accompany the estimate when present. Direction derives
from the verified directional code.

The API distinguishes a route outside coverage, missing weekday-hour data,
a disabled or missing artifact, failed artifact validation, invalid route
mapping and a failed individual lookup. Journey planning remains available
in these cases. A valid average of zero remains a displayed estimate.

```sh
scripts/validate_data feeds/delhi_buses_static_gtfs_v1.zip --origin http://127.0.0.1:8080
scripts/validate_ml
```

Coverage is also available at `/api/v1/demand/coverage`. An authorized
October ETM source and the complete directional export are needed to expand
the coverage and run a fresh holdout evaluation. Verified vehicle capacity,
boarding and alighting counts, trip identity and ground-truth passenger
loads are required for segment occupancy. [Member 1 evidence](ML_EVALUATION_REPORT.md)
