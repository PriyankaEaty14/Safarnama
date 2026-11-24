import csv
import io
import json
import sqlite3
import zipfile
from dataclasses import replace

import pytest
from fastapi.testclient import TestClient

from app.adapters.ml_adapter import SegmentPrediction
from app.core.config import Settings
from app.main import create_app
from app.services.crowding_service import checked_prediction
from app.services.gtfs_service import import_gtfs


def make_feed(tmp_path, *, trips=None, times=None, stops=None, calendars=None, dates=None, shapes=None):
    rows = {
        "agency.txt": ["agency_id,agency_name,agency_timezone", "X,Example,Asia/Kolkata"],
        "stops.txt": ["stop_id,stop_name,stop_lat,stop_lon", *(stops or ["A,Alpha,28.60,77.10", "B,Beta,28.61,77.11", "C,Gamma,28.62,77.12"])],
        "routes.txt": ["route_id,agency_id,route_type,route_short_name", "R,X,3,Bus R"],
        "calendar.txt": ["service_id,monday,tuesday,wednesday,thursday,friday,saturday,sunday,start_date,end_date", *(calendars or ["S,1,1,1,1,1,1,1,20261101,20261231"])],
        "trips.txt": ["trip_id,route_id,service_id,shape_id", *(trips or ["T,R,S,SH"])],
        "stop_times.txt": ["trip_id,arrival_time,departure_time,stop_id,stop_sequence", *(times or ["T,08:00:00,08:00:00,A,0", "T,08:10:00,08:10:00,B,1"])],
        "shapes.txt": ["shape_id,shape_pt_lat,shape_pt_lon,shape_pt_sequence", *(shapes or ["SH,28.60,77.10,0", "SH,28.61,77.11,1"])],
    }
    if dates is not None:
        rows["calendar_dates.txt"] = ["service_id,date,exception_type", *dates]
    path = tmp_path / "feed.zip"
    with zipfile.ZipFile(path, "w") as archive:
        for name, lines in rows.items():
            archive.writestr(name, "\n".join(lines) + "\n")
    return path


def client_for(tmp_path, feed):
    database = tmp_path / "feed.db"
    report = import_gtfs(feed, database)
    return TestClient(create_app(Settings(f"sqlite:///{database}", (), "WARNING"))), report


def test_missing_required_column_and_missing_calendar(tmp_path):
    feed = make_feed(tmp_path)
    with zipfile.ZipFile(feed) as archive:
        entries = {name: archive.read(name) for name in archive.namelist()}
    entries["stops.txt"] = b"stop_id,stop_name,stop_lat\nA,Alpha,28.6\n"
    with zipfile.ZipFile(feed, "w") as archive:
        for name, value in entries.items():
            archive.writestr(name, value)
    with pytest.raises(ValueError, match="missing columns"):
        import_gtfs(feed, tmp_path / "bad.db")


def test_invalid_relationship_sequence_and_duplicate_are_reported(tmp_path):
    feed = make_feed(tmp_path, times=[
        "T,08:00:00,08:00:00,A,0",
        "T,08:00:00,08:00:00,A,0",
        "T,08:01:00,08:01:00,missing,1",
        "T,08:02:00,08:02:00,B,-1",
        "T,08:10:00,08:10:00,B,2",
    ])
    _, report = client_for(tmp_path, feed)
    times = report["tables"]["stop_times.txt"]
    assert (times["imported"], times["duplicates"], times["rejected"]) == (2, 1, 2)
    assert "unknown trip_id or stop_id" in times["validation_errors"]
    assert "negative stop_sequence" in times["validation_errors"]
    assert report["tables"]["calendar_dates.txt"]["available"] is False


def test_repeat_import_and_failed_import_preserve_database(tmp_path):
    feed = make_feed(tmp_path)
    database = tmp_path / "feed.db"
    import_gtfs(feed, database)
    import_gtfs(feed, database)
    with sqlite3.connect(database) as db:
        assert db.execute("SELECT COUNT(*) FROM stop_times").fetchone()[0] == 2
    bad = make_feed(tmp_path, times=["T,08:10:00,08:10:00,A,0", "T,08:00:00,08:00:00,B,1"])
    with pytest.raises(ValueError, match="run backward"):
        import_gtfs(bad, database)
    with sqlite3.connect(database) as db:
        assert db.execute("SELECT COUNT(*) FROM stop_times").fetchone()[0] == 2


def test_transfer_limit_impossible_transfer_and_preference(tmp_path):
    trips = [f"T{i},R,S,SH" for i in range(26)] + ["CONNECT,R,S,SH"]
    times = []
    for i in range(26):
        destination = "B" if i == 25 else "X"
        times.extend([f"T{i},08:{i:02d}:00,08:{i:02d}:00,A,0", f"T{i},08:{i+10:02d}:00,08:{i+10:02d}:00,{destination},1"])
    times.extend(["CONNECT,08:40:00,08:40:00,B,0", "CONNECT,08:50:00,08:50:00,C,1"])
    feed = make_feed(tmp_path, trips=trips, times=times, stops=["A,Alpha,28.60,77.10", "B,Beta,28.61,77.11", "C,Gamma,28.62,77.12", "X,Other,28.60,77.13"])
    client, _ = client_for(tmp_path, feed)
    with client:
        query = {"origin": "A", "destination": "C", "date": "2026-11-23", "time": "08:25"}
        journeys = client.get("/api/v1/journeys", params=query).json()
        assert journeys and all(item["transfers"] == 1 for item in journeys)
        assert journeys[0]["legs"][0]["tripId"] == "T25"
        assert journeys[0]["transferDuration"] == 5
        balanced = client.get("/api/v1/journeys", params={**query, "preference": "balanced"}).json()
        assert balanced[0]["rankingStatus"] == "schedule_based"
        assert client.get("/api/v1/journeys", params={**query, "date": "2027-01-01"}).json() == []


def test_calendar_exception_and_weekend(tmp_path):
    feed = make_feed(tmp_path, calendars=["S,1,1,1,1,1,0,0,20261101,20261231"], dates=["S,20261128,1", "S,20261123,2"])
    client, _ = client_for(tmp_path, feed)
    with client:
        query = {"origin": "A", "destination": "B", "time": "07:55"}
        assert client.get("/api/v1/journeys", params={**query, "date": "2026-11-23"}).json() == []
        assert client.get("/api/v1/journeys", params={**query, "date": "2026-11-28"}).json()
        assert client.get("/api/v1/journeys", params={**query, "date": "2026-11-29"}).json() == []


def test_loop_geometry_uses_later_stop_occurrence(tmp_path):
    stops = ["A,Alpha,28.60,77.10", "B,Beta,28.61,77.11", "C,Gamma,28.62,77.12", "D,Delta,28.63,77.13"]
    times = ["T,08:00:00,08:00:00,A,0", "T,08:05:00,08:05:00,B,1", "T,08:10:00,08:10:00,C,2", "T,08:15:00,08:15:00,A,3", "T,08:20:00,08:20:00,D,4"]
    shapes = ["SH,28.60,77.10,0", "SH,28.61,77.11,1", "SH,28.62,77.12,2", "SH,28.60,77.10,3", "SH,28.63,77.13,4"]
    client, _ = client_for(tmp_path, make_feed(tmp_path, stops=stops, times=times, shapes=shapes))
    with client:
        response = client.get("/api/v1/routes/R/geometry", params={"trip_id": "T", "from_stop_sequence": 3, "to_stop_sequence": 4}).json()
        assert response["status"] == "available"
        assert response["coordinates"] == [[28.6, 77.1], [28.63, 77.13]]
        assert client.get("/api/v1/routes/R/geometry", params={"trip_id": "T", "from_stop_id": "A", "to_stop_id": "D"}).json()["status"] == "unavailable"


def test_crowding_contract_rejects_misleading_outputs():
    class Adapter:
        def __init__(self, prediction):
            self.prediction = prediction
        def lookup(self, key):
            return self.prediction
    unavailable = SegmentPrediction("unavailable", None, None, None, None, None, False)
    assert checked_prediction(Adapter(unavailable), None).historical is False
    with pytest.raises(ValueError, match="Unavailable prediction"):
        checked_prediction(Adapter(replace(unavailable, estimated_passenger_load=12)), None)
    with pytest.raises(ValueError, match="source"):
        checked_prediction(Adapter(replace(unavailable, status="available", estimated_passenger_load=12)), None)
    valid = replace(unavailable, status="historical_estimate", source="validated-test", estimated_passenger_load=12, historical=True)
    assert checked_prediction(Adapter(valid), None).estimated_passenger_load == 12


def test_journey_after_first_hundred_boardings_is_found(tmp_path):
    trips = [f"T{i},R,S,SH" for i in range(101)]
    times = []
    for i in range(100):
        hour, minute = divmod(8*60+i, 60)
        end_hour, end_minute = divmod(8*60+i+5, 60)
        times.extend([f"T{i},{hour:02d}:{minute:02d}:00,{hour:02d}:{minute:02d}:00,A,0",
                      f"T{i},{end_hour:02d}:{end_minute:02d}:00,{end_hour:02d}:{end_minute:02d}:00,X,1"])
    times.extend(["T100,09:40:00,09:40:00,A,0", "T100,09:50:00,09:50:00,B,1"])
    stops = ["A,Alpha,28.60,77.10", "B,Beta,28.61,77.11", "X,Other,28.60,77.13"]
    client, _ = client_for(tmp_path, make_feed(tmp_path, trips=trips, times=times, stops=stops))
    with client:
        journeys = client.get("/api/v1/journeys", params={"origin": "A", "destination": "B", "date": "2026-11-23", "time": "08:00"}).json()
        assert journeys and journeys[0]["legs"][0]["tripId"] == "T100"


def test_transfer_threshold_midnight_and_balanced_ranking(tmp_path):
    trips = ["DIRECT,R,S,SH", "FIRST,R,S,SH", "SECOND,R,S,SH", "TOOEARLY,R,S,SH", "NIGHT,R,S,SH"]
    times = [
        "DIRECT,08:00:00,08:00:00,A,0", "DIRECT,08:30:00,08:30:00,C,1",
        "FIRST,08:00:00,08:00:00,A,0", "FIRST,08:10:00,08:10:00,B,1",
        "TOOEARLY,08:12:00,08:12:00,B,0", "TOOEARLY,08:20:00,08:20:00,C,1",
        "SECOND,08:13:00,08:13:00,B,0", "SECOND,08:25:00,08:25:00,C,1",
        "NIGHT,23:55:00,23:55:00,A,0", "NIGHT,24:10:00,24:10:00,C,1",
    ]
    client, _ = client_for(tmp_path, make_feed(tmp_path, trips=trips, times=times))
    with client:
        query = {"origin": "A", "destination": "C", "date": "2026-11-23", "time": "07:55"}
        fastest = client.get("/api/v1/journeys", params=query).json()
        assert fastest[0]["legs"][0]["tripId"] == "FIRST"
        assert fastest[0]["legs"][1]["tripId"] == "SECOND"
        assert all(not any(leg["tripId"] == "TOOEARLY" for leg in trip["legs"]) for trip in fastest)
        balanced = client.get("/api/v1/journeys", params={**query, "preference": "balanced"}).json()
        assert balanced[0]["legs"][0]["tripId"] == "DIRECT"
        night = client.get("/api/v1/journeys", params={**query, "time": "23:50"}).json()
        assert night[0]["arrival"] == 1450
        assert client.get("/api/v1/journeys", params={**query, "origin": "C", "destination": "A"}).json() == []


def test_missing_shape_is_explicit(tmp_path):
    feed = make_feed(tmp_path, trips=["T,R,S,"])
    client, _ = client_for(tmp_path, feed)
    with client:
        result = client.get("/api/v1/routes/R/geometry", params={"trip_id": "T", "from_stop_sequence": 0, "to_stop_sequence": 1}).json()
        assert result["status"] == "unavailable"
        assert result["coordinates"] == []


def test_distinct_transfer_stops_keep_distinct_journey_ids(tmp_path):
    stops = ["A,Alpha,28.60,77.10", "B,Beta,28.61,77.11", "D,Delta,28.62,77.12", "C,Gamma,28.63,77.13"]
    trips = ["FIRST,R,S,SH", "SECOND,R,S,SH"]
    times = [
        "FIRST,08:00:00,08:00:00,A,0", "FIRST,08:10:00,08:10:00,B,1", "FIRST,08:20:00,08:20:00,D,2",
        "SECOND,08:25:00,08:25:00,B,0", "SECOND,08:30:00,08:30:00,D,1", "SECOND,08:40:00,08:40:00,C,2",
    ]
    client, _ = client_for(tmp_path, make_feed(tmp_path, stops=stops, trips=trips, times=times))
    with client:
        result = client.get("/api/v1/journeys", params={"origin": "A", "destination": "C", "date": "2026-11-23", "time": "08:00"}).json()
    assert len(result) == 2
    assert len({journey["id"] for journey in result}) == 2
    assert {journey["legs"][0]["stopIds"][-1] for journey in result} == {"B", "D"}
    for journey in result:
        identity = json.loads(journey["id"])
        assert identity[0][4] == identity[1][2]
        assert identity[0][3] == journey["legs"][0]["alightSequence"]
        assert identity[1][1] == journey["legs"][1]["boardSequence"]
        assert journey["transferDuration"] == journey["legs"][1]["start"] - journey["legs"][0]["end"]


def test_repeated_direct_destination_keeps_distinct_alighting_occurrences(tmp_path):
    trips = ["LOOP,R,S,SH"]
    times = ["LOOP,08:00:00,08:00:00,A,0", "LOOP,08:10:00,08:10:00,B,1",
             "LOOP,08:20:00,08:20:00,A,2", "LOOP,08:30:00,08:30:00,B,3"]
    client, _ = client_for(tmp_path, make_feed(tmp_path, trips=trips, times=times))
    with client:
        result = client.get("/api/v1/journeys", params={"origin": "A", "destination": "B", "date": "2026-11-23", "time": "08:00"}).json()
    assert {(journey["legs"][0]["boardSequence"], journey["legs"][0]["alightSequence"]) for journey in result} == {(0, 1), (0, 3), (2, 3)}
    assert len({journey["id"] for journey in result}) == 3


def test_six_hour_window_includes_both_boardings_at_boundary_only(tmp_path):
    trips = ["FIRST,R,S,SH", "ON_TIME,R,S,SH", "TOO_LATE,R,S,SH", "DIRECT_AT,R,S,SH", "DIRECT_LATE,R,S,SH"]
    times = [
        "FIRST,13:45:00,13:45:00,A,0", "FIRST,13:55:00,13:55:00,B,1",
        "ON_TIME,14:00:00,14:00:00,B,0", "ON_TIME,14:20:00,14:20:00,C,1",
        "TOO_LATE,14:01:00,14:01:00,B,0", "TOO_LATE,14:10:00,14:10:00,C,1",
        "DIRECT_AT,14:00:00,14:00:00,A,0", "DIRECT_AT,14:30:00,14:30:00,C,1",
        "DIRECT_LATE,14:01:00,14:01:00,A,0", "DIRECT_LATE,14:05:00,14:05:00,C,1",
    ]
    client, _ = client_for(tmp_path, make_feed(tmp_path, trips=trips, times=times))
    with client:
        result = client.get("/api/v1/journeys", params={"origin": "A", "destination": "C", "date": "2026-11-23", "time": "08:00"}).json()
    assert {tuple(leg["tripId"] for leg in journey["legs"]) for journey in result} == {("FIRST", "ON_TIME"), ("DIRECT_AT",)}
    assert all(leg["start"] <= 14 * 60 for journey in result for leg in journey["legs"])


def test_feed_transfer_minimum_and_prohibition(tmp_path):
    feed = make_feed(
        tmp_path, trips=["T1,R,S,", "T2,R,S,", "T3,R,S,"],
        stops=["A,Alpha,28.60,77.10", "B,Beta,28.61,77.11", "C,Gamma,28.62,77.12", "D,Delta,28.60,77.12"],
        times=[
            "T1,08:00:00,08:00:00,A,0", "T1,08:10:00,08:10:00,B,1",
            "T2,08:20:00,08:20:00,D,0", "T2,08:25:00,08:25:00,C,1",
            "T3,08:14:00,08:14:00,B,0", "T3,08:18:00,08:18:00,C,1",
        ],
    )
    with zipfile.ZipFile(feed, "a") as archive:
        archive.writestr(
            "transfers.txt", "from_stop_id,to_stop_id,transfer_type,min_transfer_time\nB,B,3,\nB,D,2,600\n",
        )
    client, report = client_for(tmp_path, feed)
    assert report["tables"]["transfers.txt"]["imported"] == 2
    with client:
        response = client.get("/api/v1/journeys?origin=A&destination=C&date=2026-11-24&time=08:00")
        assert client.get("/api/v1/ready").json()["schedules"] == "ready"
    assert response.status_code == 200
    journey, = response.json()
    assert journey["transferDuration"] == 10
    assert [leg["stopIds"] for leg in journey["legs"]] == [["A", "B"], ["D", "C"]]


def test_service_beyond_two_midnights_and_analytics(tmp_path):
    feed = make_feed(
        tmp_path, times=["T,49:00:00,49:00:00,A,0", "T,49:10:00,49:10:00,B,1",
                         "T,49:20:00,49:20:00,A,2", "T,49:30:00,49:30:00,B,3"],
        calendars=["S,1,1,1,1,1,1,1,20261122,20261122"],
    )
    client, _ = client_for(tmp_path, feed)
    with client:
        journeys = client.get("/api/v1/journeys?origin=A&destination=B&date=2026-11-24&time=01:00").json()
        result = client.get("/api/v1/analytics")
    assert [(journey["departure"], journey["arrival"]) for journey in journeys[:2]] == [(60, 70), (60, 90)]
    assert result.status_code == 200
    data = result.json()
    assert data["counts"]["stopTimes"] == 4
    assert [hour for hour in data["scheduledDeparturesByHour"] if hour["trips"]] == [{"hour": 49, "trips": 1}]
    assert [(link["fromStopId"], link["toStopId"], link["scheduledTraversals"])
            for link in data["corridors"]] == [("A", "B", 2), ("B", "A", 1)]
    assert data["historicalRecords"] == {"status": "unavailable", "value": None}


def test_geometry_validation_and_known_route_without_shape(tmp_path):
    client, _ = client_for(tmp_path, make_feed(tmp_path, trips=["T,R,S,"]))
    with client:
        assert client.get("/api/v1/routes/missing/geometry").status_code == 404
        result = client.get("/api/v1/routes/R/geometry")
        assert result.status_code == 200
        assert result.json()["status"] == "unavailable"
        assert result.json()["coordinates"] == []
        assert client.get("/api/v1/routes/R/geometry?trip_id=T&from_stop_sequence=0").status_code == 422
        assert client.get("/api/v1/crowding?date=invalid").status_code == 422


def test_partial_stop_times_preserve_chronological_validation(tmp_path):
    feed = make_feed(tmp_path, times=[
        "T,08:00:00,08:00:00,A,0", "T,08:15:00,,B,1", "T,,08:10:00,C,2",
    ])
    database = tmp_path / "feed.db"
    report = tmp_path / "import.json"
    with pytest.raises(ValueError, match="stop times run backward"):
        import_gtfs(feed, database, report)
    assert not database.exists()
    failure = json.loads((tmp_path / "import.failed.json").read_text())
    assert failure["consistency"]["out_of_order_stop_times"] == 1
