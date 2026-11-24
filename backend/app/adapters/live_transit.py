"""Optional Delhi Open Transit Data vehicle positions."""

from dataclasses import dataclass
from datetime import datetime, timezone
from math import isfinite
from threading import Lock
from time import monotonic
from typing import Protocol

import httpx
from google.transit import gtfs_realtime_pb2
from google.protobuf.message import DecodeError

DELHI_POSITIONS = "https://otd.delhi.gov.in/api/realtime/VehiclePositions.pb"
MAX_BYTES = 4 * 1024 * 1024
MAX_AGE_SECONDS = 120
CACHE_SECONDS = 20


@dataclass(frozen=True)
class VehiclePosition:
    latitude: float
    longitude: float
    observed_at: datetime
    feed_route_id: str | None


@dataclass(frozen=True)
class LiveSnapshot:
    status: str
    reason: str | None = None
    observed_at: datetime | None = None
    positions: tuple[VehiclePosition, ...] = ()


class LiveTransitProvider(Protocol):
    def snapshot(self) -> LiveSnapshot: ...


class DisabledLiveTransit:
    def __init__(self, enabled: bool):
        self.enabled = enabled

    def snapshot(self) -> LiveSnapshot:
        if self.enabled:
            return LiveSnapshot("unavailable", "An authorized Delhi Open Transit Data key is required.")
        return LiveSnapshot("disabled", "Live vehicle positions are disabled.")


def decode_positions(payload: bytes, now: datetime) -> LiveSnapshot:
    feed = gtfs_realtime_pb2.FeedMessage.FromString(payload)
    if not feed.IsInitialized() or not feed.header.HasField("timestamp"):
        return LiveSnapshot("unavailable", "The provider did not supply a feed timestamp.")
    timestamp = feed.header.timestamp
    now_seconds = now.timestamp()
    if not -30 <= now_seconds - timestamp <= MAX_AGE_SECONDS:
        return LiveSnapshot("stale", "The provider feed timestamp is outside the freshness window.")
    positions = []
    for entity in feed.entity:
        if not entity.HasField("vehicle"):
            continue
        vehicle = entity.vehicle
        if not vehicle.HasField("position") or not vehicle.HasField("timestamp"):
            continue
        if not -30 <= now_seconds - vehicle.timestamp <= MAX_AGE_SECONDS:
            continue
        lat, lng = vehicle.position.latitude, vehicle.position.longitude
        if not (isfinite(lat) and isfinite(lng) and -90 <= lat <= 90 and -180 <= lng <= 180):
            continue
        route = vehicle.trip.route_id if vehicle.HasField("trip") else None
        positions.append(VehiclePosition(lat, lng, datetime.fromtimestamp(vehicle.timestamp, timezone.utc),
                                         route if route and len(route) <= 200 else None))
    observed = datetime.fromtimestamp(timestamp, timezone.utc)
    return LiveSnapshot("available", observed_at=observed, positions=tuple(positions))


class DelhiLiveTransit:
    def __init__(self, key: str):
        self.key = key
        self.lock = Lock()
        self.cached: LiveSnapshot | None = None
        self.cache_until = 0.0

    def snapshot(self) -> LiveSnapshot:
        if not self.lock.acquire(blocking=False):
            return LiveSnapshot("unavailable", "The provider feed is refreshing.")
        try:
            if self.cached is None or self.cache_until <= monotonic():
                self.cached = self.fetch()
                valid_for = CACHE_SECONDS
                if self.cached.observed_at is not None:
                    oldest = min((p.observed_at for p in self.cached.positions),
                                 default=self.cached.observed_at)
                    oldest = min(oldest, self.cached.observed_at)
                    age = (datetime.now(timezone.utc) - oldest).total_seconds()
                    valid_for = max(0, min(valid_for, MAX_AGE_SECONDS - age))
                self.cache_until = monotonic() + valid_for
            return self.cached
        finally:
            self.lock.release()

    def fetch(self) -> LiveSnapshot:
        try:
            with httpx.stream("GET", DELHI_POSITIONS, params={"key": self.key},
                              timeout=httpx.Timeout(5, connect=3), follow_redirects=False) as response:
                response.raise_for_status()
                payload = bytearray()
                deadline = monotonic() + 6
                for chunk in response.iter_bytes(chunk_size=16384):
                    if len(payload) + len(chunk) > MAX_BYTES or monotonic() > deadline:
                        return LiveSnapshot("unavailable", "The provider response exceeded limits.")
                    payload.extend(chunk)
            return decode_positions(bytes(payload), datetime.now(timezone.utc))
        except (httpx.HTTPError, DecodeError, OverflowError, ValueError):
            # Upstream URLs may contain the access key.
            return LiveSnapshot("unavailable", "The provider did not return a usable vehicle feed.")
