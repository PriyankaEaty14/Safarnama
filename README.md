# Safarnama

Safarnama plans Delhi bus journeys from the published static GTFS timetable. It
compares scheduled arrival times and direct or one-transfer itineraries, shows
GTFS route shapes and summarizes the timetable. Historical ticket demand is available for 20 mapped directional routes.
Segment crowding and seat availability are unavailable.

## Run the application

Use Docker with Compose v2. From the repository root, place the supplied
`delhi_buses_static_gtfs_v1.zip` in `feeds/`, then run:

```sh
cp .env.example .env
docker compose build
docker compose run --rm backend python -m scripts.import_gtfs \
  /feeds/delhi_buses_static_gtfs_v1.zip --database /data/safarnama.db \
  --report /data/ingestion_report.json
docker compose up -d --wait
```

Open `http://127.0.0.1:8080` and try **Anand Vihar ISBT → Shivaji Stadium
Terminal** on **23 November 2026 at 08:35 IST**. For a direct option, try
**Rohini Sec 22 Terminal → Rohini Sec 23 Pocket 1 (Green Hill Aptt.)** at the
same time. API docs are at `/docs`. The Docker data volume persists across
restarts. OpenStreetMap basemap tiles and optional fonts need internet access.

## Develop locally

Use Python 3.12, Node 22.12+ and Bash. From the repository root:

```sh
scripts/setup
scripts/validate_data feeds/delhi_buses_static_gtfs_v1.zip
scripts/import_gtfs feeds/delhi_buses_static_gtfs_v1.zip
scripts/run_backend --reload --port 8000
```

From a second terminal, run `scripts/run_frontend`. See the deployment guide
before replacing an existing feed.

## Verify

```sh
npx playwright install chromium
SAFARNAMA_TEST_ORIGIN=http://127.0.0.1:5173 scripts/run_tests
```

Without a test origin, the script runs the Python suites, frontend build and
Compose validation. Chromium requires the app and imported feed.

The browser suite expects a running app with the supplied Delhi feed. It uses
`http://127.0.0.1:5173` by default. Set `SAFARNAMA_TEST_ORIGIN` to exercise a
different origin, or `SAFARNAMA_TEST_CHROMIUM` to use an installed Chromium.

- [API contract](docs/API_CONTRACT.md)
- [Deployment and feed refresh](docs/DEPLOYMENT_GUIDE.md)
- [Latest verification](docs/FINAL_TEST_REPORT.md)
- [Current feature and deployment status](docs/FINAL_PROJECT_STATUS.md)
- [Data and ML validation](docs/DATA_QUALITY_REPORT.md)
- [Member 1 handoff and historical demand](docs/ML_INTEGRATION_HANDOFF.md)
- [Integration report](docs/INTEGRATION_REPORT.md)


## Historical demand example

Search for Badarpur Border (T) to Kapashera Crossing (stop code
`EA96DE52`) on 27 November 2026 at 08:35 IST. Open the direct 717AUP
journey. The historical section shows the October weekday/hour estimate for
the route. The label describes all ticketed demand for that route-hour.
Consult the itinerary crowding status for availability of segment evidence.

The default configuration uses the bundled 3,360-row Member 1 export. Set
`SAFARNAMA_ML_ARTIFACT_DIR` to an absolute artifact directory to override it
or to an empty string to disable the feature. The planner continues to run
with no historical export. Restart after replacing the feed or artifacts.

The [schedule-only release](https://github.com/RISHI-0723/Safarnama/releases/tag/v1.0.0-schedule-based) remains available as a separate download.


The analytics view shows how many GTFS routes have verified historical demand
and lets you inspect estimates for each hour of a selected route and date.
The optional Delhi vehicle feed requires authorized access and is disabled by
default. [Data and deployment configuration](docs/DEPLOYMENT_GUIDE.md)

The planner shows upcoming departures for the current Delhi date. For a
past date, explicitly select **Historical timetable lookup**. Transfer
cards show where to alight, when to board the next bus and the scheduled
connection time. [Journey planner validation](docs/JOURNEY_PLANNER_VALIDATION.md)

Windows Docker Desktop installations can update the source without
reimporting GTFS when they keep the same Compose project and volume.
[Windows update steps](docs/DEPLOYMENT_GUIDE.md#update-an-existing-windows-docker-desktop-installation)
