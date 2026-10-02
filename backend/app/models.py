"""Drive telemetry and failure-prediction schema.

Mirrors the shape of FailSight's outputs: per-drive daily SMART readings and
per-drive failure-probability scores produced by a versioned prediction model.
"""

from datetime import date

from sqlalchemy import BigInteger, Date, Float, ForeignKey, Index, Integer, String
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


class Drive(Base):
    __tablename__ = "drives"

    serial_number: Mapped[str] = mapped_column(String(64), primary_key=True)
    model: Mapped[str] = mapped_column(String(64), index=True)
    capacity_bytes: Mapped[int] = mapped_column(BigInteger)
    datacenter: Mapped[str] = mapped_column(String(32))
    deployed_on: Mapped[date] = mapped_column(Date)
    failed_on: Mapped[date | None] = mapped_column(Date, nullable=True)

    readings: Mapped[list["SmartReading"]] = relationship(back_populates="drive")
    predictions: Mapped[list["FailurePrediction"]] = relationship(back_populates="drive")


class SmartReading(Base):
    __tablename__ = "smart_readings"
    __table_args__ = (Index("ix_smart_readings_drive_day", "serial_number", "observed_on"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    serial_number: Mapped[str] = mapped_column(ForeignKey("drives.serial_number"))
    observed_on: Mapped[date] = mapped_column(Date)
    power_on_hours: Mapped[int] = mapped_column(Integer)  # SMART 9
    reallocated_sectors: Mapped[int] = mapped_column(Integer)  # SMART 5
    reported_uncorrectable: Mapped[int] = mapped_column(Integer)  # SMART 187
    command_timeouts: Mapped[int] = mapped_column(Integer)  # SMART 188
    pending_sectors: Mapped[int] = mapped_column(Integer)  # SMART 197
    offline_uncorrectable: Mapped[int] = mapped_column(Integer)  # SMART 198
    temperature_c: Mapped[int] = mapped_column(Integer)  # SMART 194

    drive: Mapped[Drive] = relationship(back_populates="readings")


class FailurePrediction(Base):
    __tablename__ = "failure_predictions"
    __table_args__ = (Index("ix_failure_predictions_drive_day", "serial_number", "scored_on"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    serial_number: Mapped[str] = mapped_column(ForeignKey("drives.serial_number"))
    scored_on: Mapped[date] = mapped_column(Date)
    model_version: Mapped[str] = mapped_column(String(32))
    horizon_days: Mapped[int] = mapped_column(Integer)
    failure_probability: Mapped[float] = mapped_column(Float)

    drive: Mapped[Drive] = relationship(back_populates="predictions")
