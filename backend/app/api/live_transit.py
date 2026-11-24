from datetime import datetime
from typing import Literal

from fastapi import APIRouter, Query, Request, Response
from pydantic import BaseModel

from app.adapters.live_transit import VehiclePosition

router = APIRouter(prefix="/live", tags=["live transit"])


class VehiclesResponse(BaseModel):
    status: Literal["available", "disabled", "unavailable", "stale"]
    source: str = "Delhi Open Transit Data"
    reason: str | None
    observed_at: datetime | None
    vehicle_count: int
    vehicles: list[VehiclePosition]


@router.get("/vehicles", response_model=VehiclesResponse)
def vehicles(request: Request, response: Response, limit: int = Query(100, ge=1, le=500)):
    response.headers["Cache-Control"] = "no-store"
    snapshot = request.app.state.live_transit.snapshot()
    return VehiclesResponse(status=snapshot.status, reason=snapshot.reason,
                            observed_at=snapshot.observed_at, vehicle_count=len(snapshot.positions),
                            vehicles=list(snapshot.positions[:limit]))
