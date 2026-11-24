# SAFARNAMA backend

This backend imports the supplied static GTFS feed, searches scheduled direct
and one-transfer journeys, and exposes stops, routes, geometry, analytics and
explicit crowding availability through automatic OpenAPI docs.

## Run

From `backend/` on Python 3.12:

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
cp .env.example .env
set -a; source .env; set +a
python -m scripts.import_gtfs /path/to/delhi_buses_static_gtfs_v1.zip
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

Visit `http://127.0.0.1:8000/api/v1/health` for
`{"status":"ok","database":"ok"}` and `http://127.0.0.1:8000/docs`
for the interactive API docs. The SQLite file is created at `data/safarnama.db`.

```bash
python -m pytest -q
```

SQLite is suitable for the first local build. `SAFARNAMA_DATABASE_URL` and
`SAFARNAMA_CORS_ORIGINS` configure the database and allowed frontend origins.
The health endpoint checks the database connection. The readiness endpoint
`/api/v1/ready` returns HTTP 503 until schedules have been imported. The
[deployment guide](../docs/DEPLOYMENT_GUIDE.md) covers persistent storage,
feed replacement and same-origin hosting.

## Layout

- `app/main.py`: app creation, startup, CORS and error handling.
- `app/core/`: settings and logging.
- `app/db/`: SQLAlchemy engine, sessions and model base.
- `app/api/`: versioned health, stop, route, journey, crowding and analytics routes.
- `app/services/`: GTFS importer and journey search.
- `tests/`: startup and miniature GTFS integration tests.

The ETM prediction exports currently available describe historical ticketed
route demand. They cannot establish occupancy or capacity.


## Member 1 integration

The startup hook loads the bundled predictor once and verifies its manifest,
CSV, response schema and explicit directional GTFS mapping. The historical
lookup remains unavailable when this validation fails. Checkout first and
import the supplied GTFS feed before starting the server.

- `GET /api/v1/demand/historical?route_id=2171&date=2026-11-27&time=08:35`
  returns the route-hour ticket demand estimate for 717AUP.
- `GET /api/v1/crowding` validates optional GTFS segment or journey context.
  It reports unavailable crowding because the shipped export measures
  route-hour ticket demand.

See the [API contract](../docs/API_CONTRACT.md) for response examples.
