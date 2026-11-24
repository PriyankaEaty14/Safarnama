import zipfile

from fastapi.testclient import TestClient

from app.core.config import Settings
from app.main import create_app
from app.services.gtfs_service import import_gtfs


def test_import_search_calendar_overnight_and_geometry(tmp_path):
    feed = {
        "agency.txt": "agency_id,agency_name,agency_timezone\nX,Example,Asia/Kolkata\n",
        "stops.txt": "stop_id,stop_name,stop_lat,stop_lon\nA,Alpha,28.60,77.10\nB,Beta,28.61,77.11\nC,Gamma,28.62,77.12\nD,Delta,28.63,77.13\nA,Duplicate,28.60,77.10\nE,Invalid,999,77.1\n",
        "routes.txt": "route_id,agency_id,route_type,route_short_name\nR1,X,3,First\nR2,X,3,Second\n",
        "calendar.txt": "service_id,monday,tuesday,wednesday,thursday,friday,saturday,sunday,start_date,end_date\nS,1,1,1,1,1,1,1,20261101,20261231\n",
        "trips.txt": "trip_id,route_id,service_id,shape_id\nT1,R1,S,SH\nT2,R2,S,SH\nT3,R1,S,SH\n",
        "stop_times.txt": "trip_id,arrival_time,departure_time,stop_id,stop_sequence\nT1,08:00:00,08:00:00,A,0\nT1,08:10:00,08:10:00,B,1\nT2,08:15:00,08:15:00,B,0\nT2,08:25:00,08:25:00,C,1\nT3,25:00:00,25:00:00,A,0\nT3,25:10:00,25:10:00,D,1\n",
        "shapes.txt": "shape_id,shape_pt_lat,shape_pt_lon,shape_pt_sequence\nSH,28.60,77.10,0\nSH,28.61,77.11,1\n",
    }
    archive = tmp_path / "feed.zip"
    with zipfile.ZipFile(archive, "w") as writer:
        for name, content in feed.items():
            writer.writestr(name, content)
    database = tmp_path / "feed.db"
    report = import_gtfs(archive, database, tmp_path / "report.json")
    assert report["tables"]["stops.txt"]["duplicates"] == 1
    assert report["tables"]["stops.txt"]["rejected"] == 1
    assert report["tables"]["stop_times.txt"]["imported"] == 6
    app = create_app(Settings(f"sqlite:///{database}", (), "INFO"))
    with TestClient(app) as client:
        assert client.get("/api/v1/stops", params={"q": "alp"}).json()[0]["id"] == "A"
        assert client.get("/api/v1/routes/R1").json()["shortName"] == "First"
        query = {"origin": "A", "destination": "C", "date": "2026-11-23", "time": "07:55"}
        journeys = client.get("/api/v1/journeys", params=query).json()
        assert len(journeys) == 1 and journeys[0]["transfers"] == 1
        assert journeys[0]["legs"][0]["stopIds"] == ["A", "B"]
        assert client.get("/api/v1/journeys", params={**query, "date": "2027-01-01"}).json() == []
        overnight = client.get("/api/v1/journeys", params={"origin": "A", "destination": "D", "date": "2026-11-24", "time": "01:00"}).json()
        assert overnight[0]["departure"] == 60
        geometry = client.get("/api/v1/routes/R1/geometry", params={"trip_id": "T1"}).json()
        assert geometry["coordinates"] == [[28.6, 77.1], [28.61, 77.11]]
        segment = client.get("/api/v1/routes/R1/geometry", params={"trip_id": "T1", "from_stop_sequence": 0, "to_stop_sequence": 1}).json()
        assert segment["status"] == "available"
        assert client.get("/api/v1/crowding").json()["historical"] is False
        assert client.get("/api/v1/analytics").json()["counts"]["stops"] == 4
        assert client.get("/api/v1/journeys", params={**query, "time": "29:00"}).status_code == 422
        assert client.get("/api/v1/journeys", params={**query, "origin": "missing"}).status_code == 404
        assert client.get("/api/v1/stops/missing").status_code == 404
