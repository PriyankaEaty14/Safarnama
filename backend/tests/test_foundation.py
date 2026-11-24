from fastapi.testclient import TestClient
from sqlalchemy import text

from app.core.config import Settings
from app.main import create_app


def test_startup_database_health_and_docs(tmp_path):
    database = tmp_path / "safarnama.db"
    app = create_app(Settings(f"sqlite:///{database}", ("http://localhost:5173",), "INFO"))
    with TestClient(app) as client:
        assert client.get("/api/v1/health").json() == {"status": "ok", "database": "ok"}
        assert client.get("/openapi.json").status_code == 200
        with app.state.engine.connect() as connection:
            assert connection.execute(text("SELECT 1")).scalar_one() == 1
        assert client.get("/api/v1/health", headers={"Origin": "http://localhost:5173"}).headers[
            "access-control-allow-origin"
        ] == "http://localhost:5173"
    assert database.exists()


def test_readiness_and_analytics_with_empty_database(tmp_path):
    app = create_app(Settings(f"sqlite:///{tmp_path / 'empty.db'}", (), "WARNING"))
    with TestClient(app) as client:
        assert client.get("/api/v1/health").status_code == 200
        waiting = client.get("/api/v1/ready")
        assert waiting.status_code == 503
        assert waiting.json()["schedules"] == "missing"
        summary = client.get("/api/v1/analytics").json()
        assert summary["scheduledDeparturesByHour"] == summary["corridors"] == []
