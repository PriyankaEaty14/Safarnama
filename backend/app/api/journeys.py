from datetime import date, datetime, time as LocalTime
from enum import Enum
from math import ceil
from typing import Annotated, Literal
from zoneinfo import ZoneInfo
import re

from fastapi import APIRouter, HTTPException, Query, Request
from sqlalchemy import text

from app.services.journey_service import search_journeys
from app.schemas.journey import Journey


router = APIRouter(prefix="/journeys", tags=["journeys"])
DELHI = ZoneInfo("Asia/Kolkata")


class Preference(str, Enum):
    fastest = "fastest"
    balanced = "balanced"
    comfortable = "comfortable"


@router.get("", response_model=list[Journey], responses={404: {"description": "Stop not found"}, 503: {"description": "Transit database unavailable"}})
def journeys(request: Request, origin: Annotated[str, Query(min_length=1, max_length=200)], destination: Annotated[str, Query(min_length=1, max_length=200)], date: date, time: Annotated[str, Query(description="Local departure time in Asia/Kolkata, HH:MM")], preference: Preference = Preference.fastest, limit: int = Query(12, ge=1, le=30), mode: Literal["upcoming", "historical"] = "upcoming"):
    if origin == destination:
        raise HTTPException(422, "Origin and destination must differ")
    if not re.fullmatch(r"(?:[01]\d|2[0-3]):[0-5]\d", time):
        raise HTTPException(422, "time must be HH:MM in Asia/Kolkata")
    requested = (int(time[:2]) * 60 + int(time[3:])) * 60
    now = request.app.state.clock().astimezone(DELHI)
    if mode == "upcoming" and date < now.date():
        raise HTTPException(422, "This Delhi date has passed. Select historical timetable lookup to view past schedules.")
    if mode == "upcoming" and date == now.date():
        midnight = datetime.combine(date, LocalTime.min, tzinfo=DELHI)
        requested = max(requested, ceil((now - midnight).total_seconds()))
    slots = request.app.state.journey_slots
    if not slots.acquire(blocking=False):
        raise HTTPException(429, "Journey search is busy. Try again shortly.", headers={"Retry-After": "2"})
    try:
        with request.app.state.engine.connect() as db:
            found = db.execute(text("SELECT id FROM stops WHERE id IN (:origin,:destination)"), {"origin": origin, "destination": destination}).all()
            if len(found) != 2:
                raise HTTPException(404, "Origin or destination stop not found")
            return search_journeys(db, origin, destination, date, requested, limit, preference.value)
    finally:
        slots.release()
