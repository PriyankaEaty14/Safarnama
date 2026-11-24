from datetime import date
from enum import Enum
from typing import Annotated
import re

from fastapi import APIRouter, HTTPException, Query, Request
from sqlalchemy import text

from app.services.journey_service import search_journeys
from app.schemas.journey import Journey


router = APIRouter(prefix="/journeys", tags=["journeys"])


class Preference(str, Enum):
    fastest = "fastest"
    balanced = "balanced"
    comfortable = "comfortable"


@router.get("", response_model=list[Journey], responses={404: {"description": "Stop not found"}, 503: {"description": "Transit database unavailable"}})
def journeys(request: Request, origin: Annotated[str, Query(min_length=1, max_length=200)], destination: Annotated[str, Query(min_length=1, max_length=200)], date: date, time: Annotated[str, Query(description="Local departure time in Asia/Kolkata, HH:MM")], preference: Preference = Preference.fastest, limit: int = Query(12, ge=1, le=30)):
    if origin == destination:
        raise HTTPException(422, "Origin and destination must differ")
    if not re.fullmatch(r"(?:[01]\d|2[0-3]):[0-5]\d", time):
        raise HTTPException(422, "time must be HH:MM in Asia/Kolkata")
    with request.app.state.engine.connect() as db:
        found = db.execute(text("SELECT id FROM stops WHERE id IN (:origin,:destination)"), {"origin": origin, "destination": destination}).all()
        if len(found) != 2:
            raise HTTPException(404, "Origin or destination stop not found")
        requested = (int(time[:2])*60 + int(time[3:]))*60
        return search_journeys(db, origin, destination, date, requested, limit, preference.value)
