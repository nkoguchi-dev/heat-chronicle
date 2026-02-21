from datetime import date, datetime

from sqlalchemy import (
    Date,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from app.infrastructure.database import Base

SCHEMA = "heat"


class Station(Base):
    __tablename__ = "stations"
    __table_args__ = (
        UniqueConstraint("prec_no", "block_no", name="uq_stations_prec_block"),
        {"schema": SCHEMA},
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    station_name: Mapped[str] = mapped_column(String(50), nullable=False)
    prec_no: Mapped[int] = mapped_column(Integer, nullable=False)
    block_no: Mapped[str] = mapped_column(String(10), nullable=False)
    station_type: Mapped[str] = mapped_column(String(1), nullable=False)
    latitude: Mapped[float | None] = mapped_column(Float, nullable=True)
    longitude: Mapped[float | None] = mapped_column(Float, nullable=True)


class DailyTemperature(Base):
    __tablename__ = "daily_temperature"
    __table_args__ = (
        UniqueConstraint("station_id", "date", name="uq_daily_temp_station_date"),
        Index("ix_daily_temp_station_date", "station_id", "date"),
        {"schema": SCHEMA},
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    station_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("heat.stations.id"), nullable=False
    )
    date: Mapped[date] = mapped_column(Date, nullable=False)
    max_temp: Mapped[float | None] = mapped_column(Float, nullable=True)
    min_temp: Mapped[float | None] = mapped_column(Float, nullable=True)
    avg_temp: Mapped[float | None] = mapped_column(Float, nullable=True)


class FetchLog(Base):
    __tablename__ = "fetch_log"
    __table_args__ = (
        UniqueConstraint(
            "station_id", "year", "month", name="uq_fetch_log_station_year_month"
        ),
        {"schema": SCHEMA},
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    station_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("heat.stations.id"), nullable=False
    )
    year: Mapped[int] = mapped_column(Integer, nullable=False)
    month: Mapped[int] = mapped_column(Integer, nullable=False)
    fetched_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, server_default=func.now()
    )
