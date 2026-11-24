
"""SAFARNAMA historical demand integration contract.

Historical ticket demand is not actual bus occupancy,
remaining seats, or live crowdedness.
"""

from pathlib import Path
from datetime import datetime, timezone, timedelta
import math
import json
import argparse

try:
    from .demand_lookup import DemandLookup
except ImportError:
    from demand_lookup import DemandLookup


BASE = Path(__file__).resolve().parents[1]

DEFAULT_CSV = (
    BASE / "outputs" / "demo_route_predictions.csv"
)

IST = timezone(timedelta(hours=5, minutes=30))

METRIC = (
    "historical_ticketed_passengers_per_route_hour"
)


class SafarnamaPredictor:

    def __init__(self, csv_path=DEFAULT_CSV):

        self.lookup = DemandLookup(csv_path)

        self.routes = set(
            self.lookup.index.index
            .get_level_values("route")
        )

        # Additional numeric integrity checks.
        for key, row in self.lookup.index.iterrows():

            route, day, hour = key

            if not str(route).strip():
                raise ValueError("Empty route identifier")

            if int(day) != day or int(hour) != hour:
                raise ValueError(
                    "Fractional weekday or hour"
                )

            value = float(
                row["predicted_passengers"]
            )

            if not math.isfinite(value) or value < 0:
                raise ValueError(
                    "Invalid prediction value"
                )

    @staticmethod
    def get_direction(route):

        if route.endswith("DOWN"):
            return "DOWN"

        if route.endswith("UP"):
            return "UP"

        return None

    @staticmethod
    def parse_datetime(value):

        if isinstance(value, str):

            try:
                value = datetime.fromisoformat(
                    value.replace("Z", "+00:00")
                )
            except ValueError as exc:
                raise ValueError(
                    "Invalid ISO datetime"
                ) from exc

        if not isinstance(value, datetime):
            raise ValueError(
                "Datetime must be ISO string or datetime"
            )

        if value.tzinfo is None:
            raise ValueError(
                "Datetime must include timezone offset"
            )

        return value.astimezone(IST)

    @staticmethod
    def optional_number(value):

        try:
            number = float(value)
        except (ValueError, TypeError):
            return None

        if not math.isfinite(number) or number < 0:
            return None

        return number

    def predict(
        self,
        route,
        applicable_datetime,
        boarding_stop_id=None,
        alighting_stop_id=None,
        direction=None
    ):

        if not isinstance(route, str):
            raise ValueError("Route must be a string")

        route = route.strip().upper()

        if not route:
            raise ValueError("Route cannot be empty")

        inferred_direction = self.get_direction(route)

        if direction is not None:

            direction = str(direction).strip().upper()

            if direction not in {"UP", "DOWN"}:
                raise ValueError("Invalid direction")

            if (
                inferred_direction is not None
                and inferred_direction != direction
            ):
                raise ValueError(
                    "Direction conflicts with route"
                )

            if inferred_direction is None:
                raise ValueError(
                    "Use the complete directional route code"
                )

        direction = inferred_direction

        local_time = self.parse_datetime(
            applicable_datetime
        )

        weekday = local_time.weekday()
        hour = local_time.hour

        result = self.lookup.predict(
            route,
            weekday,
            hour
        )

        available = result["available"]

        if available:
            status = "available"

        elif route not in self.routes:
            status = "route_not_in_prediction_dataset"

        else:
            status = "prediction_not_available"

        historical_std = None
        historical_days = None

        if available:

            row = self.lookup.index.loc[
                (route, weekday, hour)
            ]

            historical_std = self.optional_number(
                row.get("daily_std")
            )

            days = self.optional_number(
                row.get("observed_days")
            )

            if days is not None and days.is_integer():
                historical_days = int(days)

        stop_context_requested = (
            boarding_stop_id is not None
            or alighting_stop_id is not None
        )

        return {
            "schema_version": "1.0",

            "route": route,
            "direction": direction,

            "boarding_stop_id": (
                str(boarding_stop_id)
                if boarding_stop_id is not None
                else None
            ),

            "alighting_stop_id": (
                str(alighting_stop_id)
                if alighting_stop_id is not None
                else None
            ),

            "applicable_datetime": local_time.isoformat(),

            "applicable_hour_start": (
                local_time.replace(
                    minute=0,
                    second=0,
                    microsecond=0
                ).isoformat()
            ),

            "timezone": "Asia/Kolkata",

            "day_of_week": weekday,
            "hour": hour,

            "metric": METRIC,

            "predicted_value": (
                result["predicted_passengers"]
                if available else None
            ),

            "unit": "ticketed_passengers_per_route_hour",

            "prediction_scope": "route_hour",

            "source": (
                "October_2026_ETM_historical_baseline"
            ),

            "training_period": {
                "start": "2026-10-01",
                "end": "2026-10-31"
            },

            "model": "route_weekday_hour_mean",

            "data_availability": status,

            "prediction_available": available,

            "stop_context_status": (
                "provided_not_validated"
                if stop_context_requested
                else "not_requested"
            ),

            "segment_prediction_available": False,

            "uncertainty": {
                "status": (
                    "not_calibrated"
                    if available
                    else "prediction_unavailable"
                ),

                "confidence_score": None,
                "lower_bound": None,
                "upper_bound": None,

                "historical_daily_std": historical_std,

                "historical_calendar_days": historical_days,

                "historical_days_note": (
                    "Calendar-day samples may include "
                    "zero-filled no-transaction hours."
                ),

                "note": (
                    "Historical standard deviation is "
                    "not a calibrated prediction interval."
                )
            },

            "is_live": False,
            "is_actual_occupancy": False,
            "physical_trip_verified": False,

            "actual_occupancy": None,
            "occupancy_percentage": None,
            "remaining_seats": None,
            "crowdedness_category": None,

            "display_label": (
                "Historical ticket demand"
                if available
                else "Historical demand unavailable"
            ),

            "limitations": [
                "Route-hour demand is not per-bus load.",
                "Stop IDs are request context only.",
                "Stop order must be validated by the planner.",
                "No-transaction hours may be zero-filled.",
                "No live vehicle or passenger count data.",
                "Predictions reflect October 2026 patterns.",
                "Future events and seasonal changes "
                "are not modeled."
            ]
        }


def main():

    parser = argparse.ArgumentParser(
        description="SAFARNAMA historical demand query"
    )

    parser.add_argument(
        "--csv",
        default=str(DEFAULT_CSV)
    )

    parser.add_argument(
        "--route",
        required=True
    )

    parser.add_argument(
        "--datetime",
        required=True
    )

    parser.add_argument("--boarding-stop")
    parser.add_argument("--alighting-stop")
    parser.add_argument("--direction")

    args = parser.parse_args()

    predictor = SafarnamaPredictor(args.csv)

    result = predictor.predict(
        route=args.route,
        applicable_datetime=args.datetime,
        boarding_stop_id=args.boarding_stop,
        alighting_stop_id=args.alighting_stop,
        direction=args.direction
    )

    print(
        json.dumps(
            result,
            indent=2,
            allow_nan=False
        )
    )


if __name__ == "__main__":
    main()
