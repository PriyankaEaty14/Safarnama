"""Historical route-hour ticket demand lookup. Not onboard occupancy."""
from pathlib import Path
import pandas as pd

REQUIRED = {"route", "day_of_week", "hour", "predicted_passengers"}

class DemandLookup:
    def __init__(self, csv_path):
        df = pd.read_csv(Path(csv_path), dtype={"route": str})
        missing = REQUIRED - set(df.columns)
        if missing:
            raise ValueError(f"Missing columns: {sorted(missing)}")
        if df[list(REQUIRED)].isna().any().any():
            raise ValueError("Missing values in required columns")
        if not df["day_of_week"].between(0, 6).all():
            raise ValueError("day_of_week must be 0..6")
        if not df["hour"].between(0, 23).all():
            raise ValueError("hour must be 0..23")
        if (df["predicted_passengers"] < 0).any():
            raise ValueError("Negative predicted passengers")
        keys = ["route", "day_of_week", "hour"]
        if df.duplicated(keys).any():
            raise ValueError("Duplicate route/weekday/hour keys")
        self.index = df.set_index(keys)

    def predict(self, route: str, day_of_week: int, hour: int) -> dict:
        if not isinstance(day_of_week, int) or day_of_week not in range(7):
            raise ValueError("day_of_week must be an integer from 0 to 6")
        if not isinstance(hour, int) or hour not in range(24):
            raise ValueError("hour must be an integer from 0 to 23")
        key = (route.strip().upper(), day_of_week, hour)
        if key not in self.index.index:
            return {
                "route": key[0], "day_of_week": day_of_week, "hour": hour,
                "available": False, "predicted_passengers": None,
                "metric": "historical_ticketed_passengers_per_route_hour",
                "is_live": False, "is_bus_occupancy": False
            }
        row = self.index.loc[key]
        return {
            "route": key[0], "day_of_week": day_of_week, "hour": hour,
            "available": True,
            "predicted_passengers": float(row["predicted_passengers"]),
            "metric": "historical_ticketed_passengers_per_route_hour",
            "is_live": False, "is_bus_occupancy": False
        }
