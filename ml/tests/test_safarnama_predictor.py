
import json
import pandas as pd
import pytest

from src.safarnama_predictor import SafarnamaPredictor


@pytest.fixture
def predictor(tmp_path):

    path = tmp_path / "predictions.csv"

    pd.DataFrame([
        {
            "route": "717AUP",
            "day_of_week": 4,
            "hour": 8,
            "predicted_passengers": 82.6,
            "daily_std": 12.5,
            "observed_days": 5
        },
        {
            "route": "433DOWN",
            "day_of_week": 0,
            "hour": 0,
            "predicted_passengers": 0.0,
            "daily_std": 0.0,
            "observed_days": 4
        }
    ]).to_csv(path, index=False)

    return SafarnamaPredictor(path)


TIME = "2026-11-27T08:00:00+05:30"


def test_available_prediction(predictor):

    result = predictor.predict("717AUP", TIME)

    assert result["predicted_value"] == 82.6
    assert result["prediction_available"] is True
    assert result["data_availability"] == "available"


def test_route_normalization(predictor):

    result = predictor.predict(" 717aup ", TIME)

    assert result["route"] == "717AUP"
    assert result["direction"] == "UP"


def test_missing_route(predictor):

    result = predictor.predict("UNKNOWN", TIME)

    assert result["predicted_value"] is None
    assert result["prediction_available"] is False

    assert result["data_availability"] == (
        "route_not_in_prediction_dataset"
    )


def test_missing_hour(predictor):

    result = predictor.predict(
        "717AUP",
        "2026-11-27T09:00:00+05:30"
    )

    assert result["predicted_value"] is None

    assert result["data_availability"] == (
        "prediction_not_available"
    )


def test_zero_is_available(predictor):

    result = predictor.predict(
        "433DOWN",
        "2026-11-30T00:00:00+05:30"
    )

    assert result["predicted_value"] == 0.0
    assert result["prediction_available"] is True


def test_timezone_conversion(predictor):

    result = predictor.predict(
        "717AUP",
        "2026-11-27T02:30:00Z"
    )

    assert result["hour"] == 8
    assert result["day_of_week"] == 4
    assert result["predicted_value"] == 82.6


def test_timezone_date_rollover(predictor):

    result = predictor.predict(
        "433DOWN",
        "2026-11-29T18:30:00Z"
    )

    assert result["day_of_week"] == 0
    assert result["hour"] == 0
    assert result["predicted_value"] == 0.0


def test_naive_datetime_rejected(predictor):

    with pytest.raises(ValueError):
        predictor.predict(
            "717AUP",
            "2026-11-27T08:00:00"
        )


def test_invalid_datetime(predictor):

    with pytest.raises(ValueError):
        predictor.predict("717AUP", "invalid")


def test_conflicting_direction(predictor):

    with pytest.raises(ValueError):
        predictor.predict(
            "717AUP",
            TIME,
            direction="DOWN"
        )


def test_stop_context_not_segment_prediction(predictor):

    result = predictor.predict(
        "717AUP",
        TIME,
        boarding_stop_id="123",
        alighting_stop_id="456"
    )

    assert result["boarding_stop_id"] == "123"
    assert result["alighting_stop_id"] == "456"

    assert result["prediction_scope"] == "route_hour"

    assert result["segment_prediction_available"] is False

    assert result["stop_context_status"] == (
        "provided_not_validated"
    )


def test_uncertainty_not_fabricated(predictor):

    result = predictor.predict("717AUP", TIME)

    uncertainty = result["uncertainty"]

    assert uncertainty["status"] == "not_calibrated"
    assert uncertainty["historical_daily_std"] == 12.5
    assert uncertainty["historical_calendar_days"] == 5

    assert uncertainty["confidence_score"] is None
    assert uncertainty["lower_bound"] is None
    assert uncertainty["upper_bound"] is None


def test_occupancy_claims_disabled(predictor):

    result = predictor.predict("717AUP", TIME)

    assert result["is_live"] is False
    assert result["is_actual_occupancy"] is False
    assert result["physical_trip_verified"] is False

    assert result["actual_occupancy"] is None
    assert result["remaining_seats"] is None
    assert result["occupancy_percentage"] is None
    assert result["crowdedness_category"] is None


def test_json_serialization(predictor):

    result = predictor.predict("717AUP", TIME)

    encoded = json.dumps(
        result,
        allow_nan=False
    )

    assert json.loads(encoded) == result


def test_infinite_prediction_rejected(tmp_path):

    path = tmp_path / "invalid.csv"

    pd.DataFrame([
        {
            "route": "717AUP",
            "day_of_week": 4,
            "hour": 8,
            "predicted_passengers": float("inf")
        }
    ]).to_csv(path, index=False)

    with pytest.raises(ValueError):
        SafarnamaPredictor(path)


def test_empty_route(predictor):

    with pytest.raises(ValueError):
        predictor.predict(" ", TIME)
