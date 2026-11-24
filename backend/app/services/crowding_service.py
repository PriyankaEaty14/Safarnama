import logging
from math import isfinite

from app.adapters.ml_adapter import MLAdapter, SegmentKey, SegmentPrediction, UnavailableAdapter


ALLOWED_STATUSES = {"available", "historical_estimate", "unavailable", "insufficient_data", "unsupported_segment"}
ALLOWED_CATEGORIES = {"seats_available", "standing", "crowded"}


def checked_prediction(adapter: MLAdapter, key: SegmentKey | None) -> SegmentPrediction:
    result = adapter.lookup(key)
    if not isinstance(result, SegmentPrediction) or result.status not in ALLOWED_STATUSES:
        raise ValueError("Invalid prediction status")
    if result.status in {"available", "historical_estimate"}:
        if not result.source or result.estimated_passenger_load is None or not isfinite(result.estimated_passenger_load) or result.estimated_passenger_load < 0:
            raise ValueError("Available prediction needs a source and nonnegative load")
        if result.category is not None and (result.category not in ALLOWED_CATEGORIES or result.capacity is None):
            raise ValueError("Unsupported crowd category")
        if result.confidence is not None and not 0 <= result.confidence <= 1:
            raise ValueError("Confidence must be between 0 and 1")
        if result.capacity is not None and result.capacity <= 0:
            raise ValueError("Capacity must be positive")
    elif any(value is not None for value in (result.estimated_passenger_load, result.category, result.confidence, result.capacity)):
        raise ValueError("Unavailable prediction cannot contain estimated values")
    return result


def safe_prediction(adapter: MLAdapter, key: SegmentKey | None) -> SegmentPrediction:
    try:
        return checked_prediction(adapter, key)
    except (ValueError, TypeError) as error:
        logging.getLogger(__name__).warning("Segment prediction rejected: %s", type(error).__name__)
        return UnavailableAdapter().lookup(key)
