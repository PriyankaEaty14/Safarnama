from datetime import date as ServiceDate
from typing import Annotated, Literal

from fastapi import APIRouter, HTTPException, Query, Request
from pydantic import BaseModel

from app.api.historical_demand import CLOCK
from app.adapters.ml_adapter import SegmentKey
from app.services.crowding_service import safe_prediction
from app.services.segment_context import SegmentContextError, segment_from_query, segments_from_journey


router = APIRouter(prefix="/crowding", tags=["crowding"])
Identifier = Annotated[str | None, Query(min_length=1, max_length=200)]
Direction = Literal["0", "1", "UP", "DOWN"]


class ResolvedLeg(BaseModel):
    legIndex: int
    routeId: str
    direction: str | None
    fromStopId: str
    toStopId: str
    serviceDate: ServiceDate
    minuteOfDay: int
    status: str


class CrowdingResponse(BaseModel):
    status: str
    source: str | None
    historical: bool
    estimatedPassengerLoad: float | None
    category: str | None
    confidence: float | None
    capacity: int | None
    modelVersion: str | None = None
    timeWindow: str | None = None
    segments: list[dict]
    reason: str
    legs: list[ResolvedLeg]


@router.get("", response_model=CrowdingResponse)
def crowding(
    request: Request,
    route_id: Identifier = None,
    direction: Direction | None = None,
    from_stop_id: Identifier = None,
    to_stop_id: Identifier = None,
    date: ServiceDate | None = None,
    time: Annotated[str | None, Query(pattern=CLOCK)] = None,
    journey_id: Annotated[str | None, Query(min_length=1, max_length=2048)] = None,
):
    direct_context = (route_id, from_stop_id, to_stop_id, direction)
    minute = int(time[:2]) * 60 + int(time[3:]) if time else None
    keys: list[SegmentKey] = []
    try:
        if journey_id:
            if not date or any(value is not None for value in direct_context):
                raise SegmentContextError("A journey lookup requires its search date and no segment parameters")
            with request.app.state.engine.connect() as db:
                keys = segments_from_journey(db, journey_id, date, minute)
        elif any(value is not None for value in (*direct_context, date, time)):
            if not all((route_id, from_stop_id, to_stop_id, date, time)):
                raise SegmentContextError("A segment lookup requires route_id, from_stop_id, to_stop_id, date and time")
            with request.app.state.engine.connect() as db:
                keys = [segment_from_query(db, route_id, direction, from_stop_id, to_stop_id, date, minute)]
    except SegmentContextError as error:
        raise HTTPException(error.status, str(error)) from error

    adapter = request.app.state.crowding_adapter
    if len(keys) == 1:
        predictions = [safe_prediction(adapter, keys[0])]
        headline = predictions[0]
    else:
        predictions = [safe_prediction(adapter, key) for key in keys]
        headline = safe_prediction(adapter, None)
    legs = [
        ResolvedLeg(legIndex=index, routeId=key.route_id, direction=key.direction,
                    fromStopId=key.from_stop_id, toStopId=key.to_stop_id, serviceDate=key.service_date,
                    minuteOfDay=key.minute_of_day, status=prediction.status)
        for index, (key, prediction) in enumerate(zip(keys, predictions))
    ]
    return CrowdingResponse(
        status=headline.status, source=headline.source, historical=headline.historical,
        estimatedPassengerLoad=headline.estimated_passenger_load,
        category=headline.category, confidence=headline.confidence, capacity=headline.capacity,
        modelVersion=headline.model_version, timeWindow=headline.time_window,
        segments=[], legs=legs, reason=headline.reason or "Prediction unavailable",
    )
