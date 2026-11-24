"""Stable boundary for future validated trip-segment occupancy predictions."""

from dataclasses import dataclass
from datetime import date
from typing import Protocol


@dataclass(frozen=True)
class SegmentKey:
    route_id: str
    direction: str | None
    from_stop_id: str
    to_stop_id: str
    service_date: date
    minute_of_day: int


@dataclass(frozen=True)
class SegmentPrediction:
    status: str
    estimated_passenger_load: float | None
    category: str | None
    confidence: float | None
    capacity: int | None
    source: str | None
    historical: bool
    model_version: str | None = None
    time_window: str | None = None
    reason: str | None = None


class MLAdapter(Protocol):
    def lookup(self, key: SegmentKey | None) -> SegmentPrediction: ...


class UnavailableAdapter:
    def lookup(self, key: SegmentKey | None) -> SegmentPrediction:
        return SegmentPrediction("unavailable", None, None, None, None, None, False,
                                 reason="Validated trip-segment occupancy predictions are not available.")
