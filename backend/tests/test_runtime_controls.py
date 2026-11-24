from datetime import datetime, timedelta, timezone

from fastapi.testclient import TestClient
from google.transit.gtfs_realtime_pb2 import FeedMessage

from app.adapters.live_transit import decode_positions
from app.core.config import Settings
from app.main import create_app


def test_health_request_id_and_query_limit(tmp_path):
    settings = Settings(f"sqlite:///{tmp_path / 'empty.db'}", ("https://frontend.example",), "WARNING")
    with TestClient(create_app(settings)) as client:
        health = client.get("/health", headers={"Origin": "https://frontend.example", "X-Request-ID": "spoofed"})
        assert health.status_code == 200
        assert health.headers["access-control-expose-headers"] == "X-Request-ID"
        assert health.headers["x-request-id"] != "spoofed"
        assert len(health.headers["x-request-id"]) == 32
        ready = client.get("/ready")
        assert ready.status_code == 503
        assert ready.headers["x-request-id"] != health.headers["x-request-id"]
        assert client.get("/health", params={"q": "a" * 4096}).status_code == 414


def test_live_configuration_without_credentials(tmp_path):
    for enabled, status in [(False, "disabled"), (True, "unavailable")]:
        settings = Settings(f"sqlite:///{tmp_path / 'empty.db'}", (), "WARNING", live_enabled=enabled)
        with TestClient(create_app(settings)) as client:
            response = client.get("/api/v1/live/vehicles")
            assert response.headers["cache-control"] == "no-store"
            assert response.json()["status"] == status
            assert response.json()["vehicles"] == []


def test_live_decoder_requires_fresh_timestamp_and_valid_coordinates():
    now = datetime(2026, 11, 24, tzinfo=timezone.utc)
    current = int(now.timestamp())
    feed = FeedMessage()
    feed.header.gtfs_realtime_version = "2.0"
    feed.header.timestamp = current
    for index, (timestamp, latitude) in enumerate([(current, 28.6), (current - 121, 28.7), (current, 100)]):
        entity = feed.entity.add(id=str(index))
        entity.vehicle.timestamp = timestamp
        entity.vehicle.position.latitude = latitude
        entity.vehicle.position.longitude = 77.2
    result = decode_positions(feed.SerializeToString(), now)
    assert result.status == "available"
    assert len(result.positions) == 1
    assert result.positions[0].observed_at == now
    assert decode_positions(feed.SerializeToString(), now + timedelta(seconds=121)).status == "stale"
