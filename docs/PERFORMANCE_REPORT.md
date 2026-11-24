# Performance report

24 November 2026. The baseline and revised FastAPI processes served the same
imported Delhi SQLite volume in the same container. Five repeated observations
followed the first in-container loopback request. Both processes ran in a shared
workspace, so the values describe this environment and workload.

| Endpoint workload | Baseline median ms | Revised median ms | Revised body bytes |
|---|---:|---:|---:|
| Full stop catalog | 46.37 | 49.61 | 699,811 |
| Badarpur autocomplete, up to eight stops | 1.57 | 1.73 | 853 |
| Journey, stop 2640 to 3250 on 27 Nov at 08:35 | 590.23 | 635.43 | 55,710 |
| 717AUP historical estimate | 2.28 | 2.79 | 634 |
| Warm schedule analytics | 1.16 | 5.54 | 2,771 |
| 100-stop page | — | 7.46 | 10,348 |
| Historical coverage | — | 2.15 | 1,901 |
| 24-hour historical profile | — | 35.40 | 15,274 |

The revised process took 7.20 seconds for its first schedule analytics
snapshot. The baseline was already warm. Caddy allows 20 seconds for response
headers. Under a 12-request simultaneous burst on the same journey, four
requests completed in 3.24–3.57 seconds and eight received a 429 response in
25–42 ms. The test establishes local backpressure behavior. Load capacity,
cold analytics and the planner’s full initial stop payload remain operational
limits. The paged stops API is available to clients that can fetch names in
smaller batches. [Deployment and scaling scope](DEPLOYMENT_GUIDE.md)

## Journey deduplication update

Benchmarks alternated the published baseline and revised service on the
same read-only Delhi volume. Each median uses five in-container loopback
observations after a warm-up. Other cloud verification processes shared
the environment. No capacity claim follows from these measurements.

| Workload | Baseline | Revised | Returned journeys |
|---|---:|---:|---:|
| Anand Vihar ISBT to West Enclave, historical balanced | 1,015 ms | 729 ms | 30 |
| Badarpur Border to Kapashera, historical default | 841 ms | 935 ms | 12 |

The first route pair improved in this run, while the second was slower.
The revised responses grew about 4.4% from the itinerary IDs and precise
leg times. Cached stop paths and browser stop-name indexing reduce
repeated work. SQLite's actual query plan used the existing
`ix_stop_times_stop_departure` index for a stop and time-range lookup.
Time-critical API behavior and large-catalog limits still need a staging
load test. The main JS bundle grew from 356.86 kB to approximately
358 kB before compression. [Journey validation](JOURNEY_PLANNER_VALIDATION.md)
