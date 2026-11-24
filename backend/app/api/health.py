from fastapi import APIRouter, Request, Response
from pydantic import BaseModel
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError


router = APIRouter(tags=["health"])


def liveness() -> dict[str, str]:
    return {"status": "ok"}


class HealthResponse(BaseModel):
    status: str
    database: str


class ReadinessResponse(HealthResponse):
    schedules: str


@router.get("/health", response_model=HealthResponse, responses={503: {"model": HealthResponse}})
def health(request: Request, response: Response) -> HealthResponse:
    try:
        with request.app.state.engine.connect() as connection:
            connection.execute(text("SELECT 1"))
    except SQLAlchemyError:
        response.status_code = 503
        return HealthResponse(status="degraded", database="unavailable")
    return HealthResponse(status="ok", database="ok")


@router.get("/ready", response_model=ReadinessResponse, responses={503: {"model": ReadinessResponse}})
def readiness(request: Request, response: Response) -> ReadinessResponse:
    try:
        with request.app.state.engine.connect() as connection:
            ready = connection.execute(text("""SELECT EXISTS (SELECT 1 FROM stop_times)
                                    AND EXISTS (SELECT 1 FROM trips)
                                    AND EXISTS (SELECT 1 FROM stops)
                                    AND (EXISTS (SELECT 1 FROM calendars)
                                         OR EXISTS (SELECT 1 FROM calendar_dates WHERE exception_type=1))""")).scalar_one()
    except SQLAlchemyError:
        response.status_code = 503
        return ReadinessResponse(status="degraded", database="unavailable", schedules="unknown")
    if not ready:
        response.status_code = 503
        return ReadinessResponse(status="degraded", database="ok", schedules="missing")
    return ReadinessResponse(status="ok", database="ok", schedules="ready")
