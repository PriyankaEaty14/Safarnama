from pydantic import BaseModel, Field


class StopSchedule(BaseModel):
    arrival: int | None
    departure: int | None


class Segment(BaseModel):
    from_stop: str = Field(alias="from")
    to: str
    level: str | None


class Leg(BaseModel):
    tripId: str
    routeId: str
    route: str
    boardSequence: int
    alightSequence: int
    direction: str | None
    stopIds: list[str]
    stopTimes: list[StopSchedule]
    start: int
    end: int
    segments: list[Segment]


class Journey(BaseModel):
    id: str
    departure: int
    arrival: int
    duration: int
    transfers: int
    transferDuration: int
    legs: list[Leg]
    coverage: float
    busiest: Segment | None
    confidence: float | None
    crowdingStatus: str
    rankingStatus: str
