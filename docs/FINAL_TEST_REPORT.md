# Final test report

Verification run on 24 November 2026. Baseline checkout
`6de8b403a1efd0efa89070b6488ceeb73aef26b8` had 28 backend, 43 automated ML
and 7 Chromium tests passing. The old unrestricted ML pytest collection also
tried to execute a Parquet diagnostic with missing data and dependencies. The
automated collection now targets `ml/tests`. The research diagnostic remains
available separately when its inputs exist.

| Check | Revised result |
|---|---|
| Backend pytest | 33 passed, one Starlette TestClient deprecation warning |
| Member 1 automated ML | 43 passed |
| Member 1 real export utility | Matched the original CSV value 82.6 and exercised missing route behavior |
| Vite production build | Passed, with existing React Router bundler warnings |
| Chromium | 8 passed against Chromium |
| Docker Compose config | Passed |
| Caddyfile validation | Passed using the existing Caddy container |
| Health and readiness | Both HTTP 200 with actual Delhi data. Empty database readiness returns 503 in tests. |
| Real GTFS and artifact validation | Matches archive and import digest, 20 mapped routes, 3,360 verified historical keys |
| Live integration | Disabled response and protobuf freshness/coordinate tests passed. Authorized upstream requests require a key. |
| Fresh Docker backend image | Blocked by workspace disk exhaustion during the VFS layer build. |

The app test server used the revised FastAPI files in the existing Python
container with the GTFS database mounted read-only. A local Vite production
preview served the rebuilt frontend. Browser fault paths intercept calls as
test fixtures. Successful journeys, map geometry and historical examples use
the real feed and historical artifact. The tests suppress external map tile
and font downloads to exercise map geometry independently of third-party
network access.

Use `scripts/run_tests` for Python, the frontend build and Compose validation.
Set `SAFARNAMA_TEST_ORIGIN` to include health probes and Chromium against a
server with the supplied feed. [Reproduce deployment and tests](DEPLOYMENT_GUIDE.md)
