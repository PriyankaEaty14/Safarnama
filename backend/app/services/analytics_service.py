"""Aggregate static schedules independently of passenger data."""

from datetime import date, timedelta
from threading import Lock

from pydantic import BaseModel
from sqlalchemy import Engine, text

from app.services.journey_service import active_services


class Counts(BaseModel):
    agencies: int
    stops: int
    routes: int
    trips: int
    stopTimes: int


class ServiceDates(BaseModel):
    first: str | None
    last: str | None


class ScheduledHour(BaseModel):
    hour: int
    trips: int


class ScheduledServiceDay(BaseModel):
    serviceDate: date
    weekend: bool
    trips: int


class Corridor(BaseModel):
    fromStopId: str
    fromStopName: str
    toStopId: str
    toStopName: str
    scheduledTraversals: int
    distinctRoutes: int


class UnavailableValue(BaseModel):
    status: str = "unavailable"
    value: None = None


class UnavailableSeries(BaseModel):
    status: str = "unavailable"
    values: list = []


class AnalyticsResponse(BaseModel):
    counts: Counts
    serviceDates: ServiceDates
    scheduledDeparturesByHour: list[ScheduledHour]
    corridors: list[Corridor]
    scheduledServiceWeek: list[ScheduledServiceDay]
    historicalRecords: UnavailableValue = UnavailableValue()
    hourlyDemand: UnavailableSeries = UnavailableSeries()
    routeDemand: UnavailableSeries = UnavailableSeries()
    peakHours: UnavailableSeries = UnavailableSeries()
    weekdayWeekend: UnavailableSeries = UnavailableSeries()
    crowdingDistribution: UnavailableSeries = UnavailableSeries()


def summarize(engine: Engine) -> AnalyticsResponse:
    with engine.connect() as db:
        counts = db.execute(text("""
            SELECT (SELECT COUNT(*) FROM agencies) AS agencies,
                   (SELECT COUNT(*) FROM stops) AS stops,
                   (SELECT COUNT(*) FROM routes) AS routes,
                   (SELECT COUNT(*) FROM trips) AS trips,
                   (SELECT COUNT(*) FROM stop_times) AS "stopTimes"
        """)).mappings().one()
        first, last = db.execute(text("""
            SELECT MIN(start_date), MAX(end_date) FROM (
                SELECT start_date, end_date FROM calendars
                WHERE monday + tuesday + wednesday + thursday + friday + saturday + sunday > 0
                UNION ALL
                SELECT date, date FROM calendar_dates WHERE exception_type=1
            ) AS published_dates
        """)).one()
        week = []
        if first and last:
            first_day, last_day = date.fromisoformat(first), date.fromisoformat(last)
            trips_by_service = dict(db.execute(text(
                "SELECT service_id, COUNT(*) FROM trips GROUP BY service_id"
            )).all())
            for offset in range(min(7, (last_day - first_day).days + 1)):
                day = first_day + timedelta(days=offset)
                week.append(ScheduledServiceDay(
                    serviceDate=day, weekend=day.weekday() >= 5,
                    trips=sum(trips_by_service.get(service, 0) for service in active_services(db, day)),
                ))
        hours = dict(db.execute(text("""
            SELECT CAST(first_departure / 3600 AS INTEGER) AS hour, COUNT(*)
            FROM (
                SELECT MIN(departure) AS first_departure FROM stop_times
                WHERE departure IS NOT NULL GROUP BY trip_id
            ) AS departures
            GROUP BY hour ORDER BY hour
        """)).all())
        corridors = db.execute(text("""
            WITH next_stops AS (
                SELECT trip_id, stop_id,
                       LEAD(stop_id) OVER (PARTITION BY trip_id ORDER BY stop_sequence) AS next_stop_id
                FROM stop_times
            ), busiest AS (
                SELECT stop_id, next_stop_id, COUNT(*) AS traversals,
                       COUNT(DISTINCT trips.route_id) AS routes
                FROM next_stops JOIN trips ON trips.id=next_stops.trip_id
                WHERE next_stop_id IS NOT NULL AND stop_id<>next_stop_id
                GROUP BY stop_id, next_stop_id
                ORDER BY traversals DESC, stop_id, next_stop_id LIMIT 10
            )
            SELECT a.id AS "fromStopId", a.name AS "fromStopName",
                   b.id AS "toStopId", b.name AS "toStopName",
                   traversals AS "scheduledTraversals", routes AS "distinctRoutes"
            FROM busiest JOIN stops a ON a.id=stop_id JOIN stops b ON b.id=next_stop_id
            ORDER BY traversals DESC, a.id, b.id
        """)).mappings().all()
    return AnalyticsResponse(
        counts=Counts(**counts),
        serviceDates=ServiceDates(first=first, last=last),
        scheduledDeparturesByHour=[
            ScheduledHour(hour=hour, trips=hours.get(hour, 0))
            for hour in range(max(23, max(hours)) + 1)
        ] if hours else [],
        scheduledServiceWeek=week,
        corridors=[Corridor(**row) for row in corridors],
    )


class AnalyticsService:
    """Reuse the summary for the life of a worker. Feed refresh restarts workers."""

    def __init__(self, engine: Engine):
        self.engine = engine
        self.lock = Lock()
        self.summary: AnalyticsResponse | None = None

    def get(self) -> AnalyticsResponse:
        with self.lock:
            if self.summary is None:
                result = summarize(self.engine)
                if result.counts.trips:
                    self.summary = result
                return result
            return self.summary
