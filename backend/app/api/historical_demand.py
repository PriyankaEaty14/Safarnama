"""Historical route-hour ticket estimates, kept separate from crowding."""

from datetime import date as ServiceDate, datetime, timedelta, timezone
import logging
from typing import Annotated, Literal

from fastapi import APIRouter, HTTPException, Query, Request
from pydantic import BaseModel
from sqlalchemy import func, select

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
    date: ServiceDate,
    time: Annotated[str, Query(pattern=CLOCK)],
):
    require_route(request, route_id)
    return demand_for_time(request, route_id, date, time)


def require_route(request, route_id):
    with request.app.state.session_factory() as db:
        if db.get(Route, route_id) is None:
            raise HTTPException(404, "GTFS route not found")


def demand_for_time(request, route_id, date, time):
    at = datetime.combine(date, datetime.strptime(time, "%H:%M").time(), tzinfo=DELHI)
    base = dict(route_id=route_id, day_of_week=at.weekday(), hour=at.hour,
                applicable_hour_start=at.replace(minute=0).isoformat())
    adapter = request.app.state.historical_demand
    if adapter is None:
        return HistoricalDemandResponse(status="unavailable", reason="No validated historical export is loaded.", **base)
    try:
        result = adapter.lookup(route_id, at)
    except Exception as error:
        logger.warning("Historical lookup rejected request_id=%s type=%s",
                       request.state.request_id, type(error).__name__)
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


class CoverageRoute(BaseModel):
    route_id: str
    route: str
    available_buckets: int
    sample_buckets: Literal[168] = 168


class CoverageResponse(BaseModel):
    status: Literal["available", "unavailable"]
    mapped_routes: int = 0
    imported_routes: int
    uncovered_routes: int
    export_routes: int = 0
    export_rows: int = 0
    missing_export_buckets: int = 0
    artifact_sha256: str | None = None
    routes: list[CoverageRoute]


@router.get("/coverage", response_model=CoverageResponse)
def coverage(request: Request, limit: int = Query(100, ge=1, le=250),
             offset: int = Query(0, ge=0, le=100000)):
    adapter = request.app.state.historical_demand
    if adapter is None:
        with request.app.state.engine.connect() as db:
            imported = db.execute(select(func.count()).select_from(Route)).scalar_one()
        return CoverageResponse(status="unavailable", imported_routes=imported,
                                uncovered_routes=imported, routes=[])
    ordered = sorted(adapter.routes.items(), key=lambda item: (item[1], item[0]))
    return CoverageResponse(
        status="available", mapped_routes=len(ordered), imported_routes=adapter.gtfs_route_count,
        uncovered_routes=adapter.gtfs_route_count - len(ordered), export_routes=len(adapter.bucket_counts),
        export_rows=adapter.prediction_rows, artifact_sha256=adapter.artifact_sha256,
        missing_export_buckets=len(adapter.bucket_counts) * 168 - adapter.prediction_rows,
        routes=[CoverageRoute(route_id=route_id, route=code, available_buckets=adapter.bucket_counts[code])
                for route_id, code in ordered[offset:offset + limit]],
    )


class HistoricalProfile(BaseModel):
    route_id: str
    date: ServiceDate
    hours: list[HistoricalDemandResponse]


@router.get("/profile", response_model=HistoricalProfile)
def profile(request: Request, route_id: Annotated[str, Query(min_length=1, max_length=200)], date: ServiceDate):
    require_route(request, route_id)
    return HistoricalProfile(route_id=route_id, date=date, hours=[
        demand_for_time(request, route_id, date, f"{hour:02d}:00") for hour in range(24)
    ])
