import sys
from pathlib import Path
import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from demand_lookup import DemandLookup

@pytest.fixture
def lookup(tmp_path):
    path = tmp_path / "demo.csv"
    pd.DataFrame([
        {"route": "717AUP", "day_of_week": 4, "hour": 8, "predicted_passengers": 82.6},
    ]).to_csv(path, index=False)
    return DemandLookup(path)

def test_found(lookup):
    result = lookup.predict("717aup", 4, 8)
    assert result["available"]
    assert result["predicted_passengers"] == 82.6
    assert result["is_bus_occupancy"] is False

def test_missing_is_not_zero(lookup):
    result = lookup.predict("NOT_A_ROUTE", 4, 8)
    assert result["available"] is False
    assert result["predicted_passengers"] is None

@pytest.mark.parametrize("day,hour", [(-1, 8), (7, 8), (4, 24)])
def test_bad_time(lookup, day, hour):
    with pytest.raises(ValueError):
        lookup.predict("717AUP", day, hour)

def test_duplicate_rejected(tmp_path):
    path = tmp_path / "dup.csv"
    pd.DataFrame([
        {"route": "A", "day_of_week": 0, "hour": 8, "predicted_passengers": 1},
        {"route": "A", "day_of_week": 0, "hour": 8, "predicted_passengers": 2},
    ]).to_csv(path, index=False)
    with pytest.raises(ValueError):
        DemandLookup(path)
