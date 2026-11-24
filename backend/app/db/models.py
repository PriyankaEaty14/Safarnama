from sqlalchemy import Float, ForeignKey, Index, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class Agency(Base):
    __tablename__ = "agencies"
    id: Mapped[str] = mapped_column(String, primary_key=True)
    name: Mapped[str] = mapped_column(String, nullable=False)
    timezone: Mapped[str] = mapped_column(String, nullable=False)


class Stop(Base):
    __tablename__ = "stops"
    id: Mapped[str] = mapped_column(String, primary_key=True)
    code: Mapped[str | None] = mapped_column(String)
    name: Mapped[str] = mapped_column(String, nullable=False, index=True)
    lat: Mapped[float] = mapped_column(Float, nullable=False)
    lng: Mapped[float] = mapped_column(Float, nullable=False)


class Route(Base):
    __tablename__ = "routes"
    id: Mapped[str] = mapped_column(String, primary_key=True)
    agency_id: Mapped[str] = mapped_column(ForeignKey("agencies.id"), nullable=False)
    short_name: Mapped[str | None] = mapped_column(String)
    long_name: Mapped[str | None] = mapped_column(String)
    description: Mapped[str | None] = mapped_column(String)
    route_type: Mapped[int] = mapped_column(Integer)


class Calendar(Base):
    __tablename__ = "calendars"
    id: Mapped[str] = mapped_column(String, primary_key=True)
    monday: Mapped[int] = mapped_column(Integer)
    tuesday: Mapped[int] = mapped_column(Integer)
    wednesday: Mapped[int] = mapped_column(Integer)
    thursday: Mapped[int] = mapped_column(Integer)
    friday: Mapped[int] = mapped_column(Integer)
    saturday: Mapped[int] = mapped_column(Integer)
    sunday: Mapped[int] = mapped_column(Integer)
    start_date: Mapped[str] = mapped_column(String)
    end_date: Mapped[str] = mapped_column(String)


class CalendarDate(Base):
    __tablename__ = "calendar_dates"
    service_id: Mapped[str] = mapped_column(String, primary_key=True)
    date: Mapped[str] = mapped_column(String, primary_key=True)
    exception_type: Mapped[int] = mapped_column(Integer)


class Trip(Base):
    __tablename__ = "trips"
    id: Mapped[str] = mapped_column(String, primary_key=True)
    route_id: Mapped[str] = mapped_column(ForeignKey("routes.id"), index=True)
    service_id: Mapped[str] = mapped_column(String, index=True)
    headsign: Mapped[str | None] = mapped_column(String)
    direction_id: Mapped[str | None] = mapped_column(String)
    shape_id: Mapped[str | None] = mapped_column(String)


class StopTime(Base):
    __tablename__ = "stop_times"
    trip_id: Mapped[str] = mapped_column(ForeignKey("trips.id"), primary_key=True)
    stop_sequence: Mapped[int] = mapped_column(Integer, primary_key=True)
    stop_id: Mapped[str] = mapped_column(ForeignKey("stops.id"), index=True)
    arrival: Mapped[int | None] = mapped_column(Integer)
    departure: Mapped[int | None] = mapped_column(Integer)
    __table_args__ = (Index("ix_stop_times_stop_departure", "stop_id", "departure"),)


class ShapePoint(Base):
    __tablename__ = "shape_points"
    shape_id: Mapped[str] = mapped_column(String, primary_key=True)
    sequence: Mapped[int] = mapped_column(Integer, primary_key=True)
    lat: Mapped[float] = mapped_column(Float)
    lng: Mapped[float] = mapped_column(Float)


class Transfer(Base):
    __tablename__ = "transfers"
    from_stop_id: Mapped[str] = mapped_column(ForeignKey("stops.id"), primary_key=True)
    to_stop_id: Mapped[str] = mapped_column(ForeignKey("stops.id"), primary_key=True)
    transfer_type: Mapped[int] = mapped_column(Integer)
    min_transfer_time: Mapped[int | None] = mapped_column(Integer)
