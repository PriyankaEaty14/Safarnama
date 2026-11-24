import csv
from datetime import date
from hashlib import file_digest
import json
from pathlib import Path
from shutil import copytree

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text

from app.adapters.historical_demand import MAPPING
from app.core.config import Settings
from app.main import create_app
from test_regressions import client_for, make_feed

ARTIFACTS = Path(__file__).resolve().parents[2] / "ml" / "outputs"
URL = "/api/v1/demand/historical"
QUERY = {"route_id": "2171", "date": "2026-11-27", "time": "08:35"}


@pytest.fixture
def demand_client(tmp_path):
    def make_client(directory=ARTIFACTS, ambiguous=False, mapping=None):
        database = tmp_path / "demand.db"
        setup = create_app(Settings(f"sqlite:///{database}", (), "WARNING"))
        with TestClient(setup):
            rows = json.loads(MAPPING.read_text())["routes"]
            with setup.state.engine.begin() as db:
                db.execute(text("INSERT INTO agencies VALUES ('DTC','DTC','Asia/Kolkata'),"
                                "('DIMTS','DIMTS','Asia/Kolkata')"))
                db.execute(text("""
                    INSERT INTO routes (id, short_name, long_name, agency_id, route_type)
                    VALUES (:gtfs_route_id,:etm_route_code,:etm_route_code,:agency_id,3)
                """), rows)
                db.execute(text("INSERT INTO routes (id,short_name,agency_id,route_type)"
                                " VALUES ('other',:name,'DTC',3)"),
                           {"name": "717AUP" if ambiguous else "UNMAPPED"})
        return TestClient(create_app(Settings(f"sqlite:///{database}", (), "WARNING", directory, mapping)))
    return make_client


def test_actual_export_matches_gtfs_and_historical_response(demand_client):
    with (ARTIFACTS / "demo_route_predictions.csv").open() as csv_file:
        expected = next(row for row in csv.DictReader(csv_file)
                        if (row["route"], row["day_of_week"], row["hour"]) == ("717AUP", "4", "8"))
    with demand_client() as client:
        response = client.get(URL, params=QUERY)
        assert response.status_code == 200
        result = response.json()
        assert result["status"] == "historical_estimate"
        assert result["route"] == "717AUP"
        assert result["estimated_ticketed_passengers"] == float(expected["predicted_passengers"])
        assert result["historical_daily_std"] == float(expected["daily_std"])
        assert result["historical_calendar_days"] == int(expected["observed_days"])
        assert result["applicable_hour_start"] == "2026-11-27T08:00:00+05:30"
        assert result["is_live"] is result["is_actual_occupancy"] is False
        assert client.get(URL, params={**QUERY, "route_id": "other"}).json()["status"] == "unsupported_route"
        assert client.get(URL, params={**QUERY, "route_id": "unknown"}).status_code == 404
        assert client.get(URL, params={**QUERY, "time": "25:01"}).status_code == 422
        assert client.get(URL, params={**QUERY, "date": "2026-02-30"}).status_code == 422


def test_zero_demand_is_preserved(demand_client):
    with demand_client() as client:
        result = client.get(URL, params={"route_id": "1931", "date": str(date(2026, 11, 23)),
                                         "time": "00:00"}).json()
        assert result["status"] == "historical_estimate"
        assert result["estimated_ticketed_passengers"] == 0


@pytest.mark.parametrize("reason", ["absent", "checksum", "ambiguous"])
def test_invalid_or_missing_artifacts_fail_closed(tmp_path, demand_client, reason):
    directory = ARTIFACTS
    if reason == "absent":
        directory = tmp_path / "missing"
    if reason == "checksum":
        directory = tmp_path / "changed"
        copytree(ARTIFACTS, directory)
        with (directory / "demo_route_predictions.csv").open("a") as artifact:
            artifact.write("\n")
    with demand_client(directory, ambiguous=reason == "ambiguous") as client:
        result = client.get(URL, params=QUERY).json()
        assert result["status"] == "unavailable"
        assert result["estimated_ticketed_passengers"] is None
        assert client.get("/api/v1/health").status_code == 200


def test_sparse_export_and_malformed_prediction_fallback(tmp_path, demand_client, monkeypatch):
    directory = tmp_path / "sparse"
    copytree(ARTIFACTS, directory)
    csv_path = directory / "demo_route_predictions.csv"
    rows = csv_path.read_text().splitlines()
    keep = [line for line in rows if not line.startswith("717AUP,4,8,")]
    assert len(rows) - len(keep) == 1
    csv_path.write_text("\n".join(keep) + "\n")
    manifest_path = directory / "safarnama_prediction_manifest.json"
    manifest = json.loads(manifest_path.read_text())
    manifest["prediction_rows"] -= 1
    with csv_path.open("rb") as artifact:
        manifest["sha256"] = file_digest(artifact, "sha256").hexdigest()
    manifest_path.write_text(json.dumps(manifest))
    with demand_client(directory) as client:
        result = client.get(URL, params=QUERY).json()
        assert result["status"] == "insufficient_data"
        assert result["estimated_ticketed_passengers"] is None
        predictor = client.app.state.historical_demand.predictor
        original = predictor.predict
        monkeypatch.setattr(predictor, "predict", lambda **kwargs: {
            **original(**kwargs), "is_actual_occupancy": True, "remaining_seats": 10,
        })
        result = client.get(URL, params=QUERY).json()
        assert result["status"] == "unavailable"
        assert result["estimated_ticketed_passengers"] is None


def test_crowding_resolves_a_scheduled_leg_without_inventing_capacity(tmp_path):
    client, _ = client_for(tmp_path, make_feed(tmp_path))
    direct = {"route_id": "R", "from_stop_id": "A", "to_stop_id": "B",
              "date": "2026-11-23", "time": "08:00"}
    path = "/api/v1/crowding"
    with client:
        resolved = client.get(path, params=direct).json()
        assert resolved["status"] == "unavailable"
        assert resolved["legs"] == [{
            "legIndex": 0, "routeId": "R", "direction": None, "fromStopId": "A", "toStopId": "B",
            "serviceDate": "2026-11-23", "minuteOfDay": 480, "status": "unavailable",
        }]
        assert all(resolved[key] is None for key in ("estimatedPassengerLoad", "category", "confidence", "capacity"))
        assert client.get(path, params={**direct, "direction": "UP"}).status_code == 422
        assert client.get(path, params={**direct, "from_stop_id": "Q"}).status_code == 404
        assert client.get(path, params={**direct, "from_stop_id": "B", "to_stop_id": "A"}).status_code == 422
        assert client.get(path, params={**direct, "date": "2027-01-01"}).status_code == 422
        assert client.get(path, params={"route_id": "R"}).status_code == 422
        journey = client.get("/api/v1/journeys", params={
            "origin": "A", "destination": "B", "date": direct["date"], "time": "07:55",
        }).json()[0]
        query = {"journey_id": journey["id"], "date": direct["date"], "time": "07:55"}
        assert client.get(path, params=query).json()["legs"] == resolved["legs"]
        assert client.get(path, params={**query, "journey_id": "[1]"}).status_code == 422


def test_overnight_journey_resolves_original_service_day(tmp_path):
    client, _ = client_for(tmp_path, make_feed(tmp_path, times=[
        "T,25:00:00,25:00:00,A,0", "T,25:10:00,25:10:00,B,1",
    ]))
    with client:
        query = {"origin": "A", "destination": "B", "date": "2026-11-24", "time": "00:55"}
        found = client.get("/api/v1/journeys", params=query).json()[0]
        result = client.get("/api/v1/crowding", params={
            "journey_id": found["id"], "date": query["date"], "time": query["time"],
        }).json()
        assert result["legs"][0]["serviceDate"] == "2026-11-23"
        assert result["legs"][0]["minuteOfDay"] == 60


def test_coverage_pagination_and_profile_use_artifact(demand_client):
    with demand_client() as client:
        coverage = client.get("/api/v1/demand/coverage", params={"limit": 1}).json()
        second = client.get("/api/v1/demand/coverage", params={"limit": 1, "offset": 1}).json()
        assert (coverage["mapped_routes"], coverage["uncovered_routes"]) == (20, 1)
        assert (coverage["export_rows"], coverage["missing_export_buckets"]) == (3360, 0)
        assert coverage["routes"][0] != second["routes"][0]
        params = {key: QUERY[key] for key in ("route_id", "date")}
        hours = client.get("/api/v1/demand/profile", params=params).json()["hours"]
        assert [item["hour"] for item in hours] == list(range(24))
        assert hours[8] == client.get(URL, params=QUERY).json()


def test_named_export_and_reviewed_partial_crosswalk(tmp_path, demand_client):
    directory = tmp_path / "export"
    copytree(ARTIFACTS, directory)
    manifest_path = directory / "safarnama_prediction_manifest.json"
    manifest = json.loads(manifest_path.read_text())
    (directory / manifest["dataset"]).rename(directory / "network_routes.csv")
    manifest["dataset"] = "network_routes.csv"
    manifest["coverage_scope"] = "full_network"
    manifest_path.write_text(json.dumps(manifest))

    mapping = tmp_path / "crosswalk.json"
    crosswalk = json.loads(MAPPING.read_text())
    crosswalk["routes"] = [row for row in crosswalk["routes"] if row["gtfs_route_id"] == "2171"]
    mapping.write_text(json.dumps(crosswalk))
    with demand_client(directory, mapping=mapping) as client:
        coverage = client.get("/api/v1/demand/coverage").json()
        assert coverage["mapped_routes"] == 1
        assert coverage["export_routes"] == 20
        assert client.get(URL, params=QUERY).json()["estimated_ticketed_passengers"] == 82.6
        assert client.get(URL, params={**QUERY, "route_id": "1931"}).json()["status"] == "unsupported_route"
