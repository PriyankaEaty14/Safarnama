"""Historical route-hour ticket estimates, kept separate from crowding."""

from datetime import date, datetime, timedelta, timezone
import logging
from typing import Annotated, Literal

from fastapi import APIRouter, HTTPException, Query, Request
from pydantic import BaseModel

from app.adapters.historical_demand import METRIC
from app.db.models import Route

router = APIRouter(prefix="/demand", tags=["historical demand"])
logger = logging.getLogger(__name__)
DELHI = timezone(timedelta(hours=5, minutes=30))
CLOCK = r"^(?:[01][0-9]|2[0-3]):[0-5][0-9]$"


class HistoricalDemandResponse(BaseModel):
    status: Literal["historical_estimate", "unavailable", "insufficient_data", "unsupported_route"]
    route_id: str
    route: str | None = None
    day_of_week: int
    hour: int
    applicable_hour_start: str
    timezone: Literal["Asia/Kolkata"] = "Asia/Kolkata"
    metric: Literal["historical_ticketed_passengers_per_route_hour"] = METRIC
    unit: Literal["ticketed_passengers_per_route_hour"] = "ticketed_passengers_per_route_hour"
    label: str = "Historical estimated ticket demand"
    estimated_ticketed_passengers: float | None = None
    historical_daily_std: float | None = None
    historical_calendar_days: int | None = None
    source: str | None = None
    model: str | None = None
    schema_version: str | None = None
    training_period: dict[str, str] | None = None
    is_live: Literal[False] = False
    is_actual_occupancy: Literal[False] = False
    reason: str | None = None


@router.get("/historical", response_model=HistoricalDemandResponse)
def historical_demand(
    request: Request,
    route_id: Annotated[str, Query(min_length=1, max_length=200)],
    date: date,
    time: Annotated[str, Query(pattern=CLOCK)],
):
    with request.app.state.session_factory() as db:
        if db.get(Route, route_id) is None:
            raise HTTPException(404, "GTFS route not found")
    at = datetime.combine(date, datetime.strptime(time, "%H:%M").time(), tzinfo=DELHI)
    base = dict(route_id=route_id, day_of_week=at.weekday(), hour=at.hour,
                applicable_hour_start=at.replace(minute=0).isoformat())
    adapter = request.app.state.historical_demand
    if adapter is None:
        return HistoricalDemandResponse(status="unavailable", reason="No validated historical export is loaded.", **base)
    try:
        result = adapter.lookup(route_id, at)
    except Exception as error:
        logger.warning("Historical lookup rejected", extra={"route_id": route_id, "error_type": type(error).__name__})
        return HistoricalDemandResponse(status="unavailable", reason="The historical estimate failed validation.", **base)
    if result is None:
        return HistoricalDemandResponse(status="unsupported_route", reason="This route is outside the verified historical dataset.", **base)
    available = result["prediction_available"]
    return HistoricalDemandResponse(
        status="historical_estimate" if available else "insufficient_data",
        reason=None if available else "No estimate is available for this weekday and hour.",
        route=result["route"], estimated_ticketed_passengers=result["predicted_value"],
        historical_daily_std=result["uncertainty"]["historical_daily_std"],
        historical_calendar_days=result["uncertainty"]["historical_calendar_days"],
        source=result["source"], model=result["model"], schema_version=result["schema_version"],
        training_period=result["training_period"], **base,
    )
