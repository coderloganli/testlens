"""Read-only queries over the test data. Every function returns JSON-safe rows."""

from datetime import timedelta
from typing import Any

from sqlalchemy import Select, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Drive, FailurePrediction, SmartReading

Row = dict[str, Any]


def _latest_predictions() -> Select:
    """Latest failure-prediction row per drive."""
    latest = (
        select(
            FailurePrediction.serial_number,
            func.max(FailurePrediction.scored_on).label("scored_on"),
        )
        .group_by(FailurePrediction.serial_number)
        .subquery()
    )
    return select(FailurePrediction).join(
        latest,
        (FailurePrediction.serial_number == latest.c.serial_number)
        & (FailurePrediction.scored_on == latest.c.scored_on),
    )


async def fleet_summary(session: AsyncSession) -> list[Row]:
    latest = _latest_predictions().subquery()
    stmt = (
        select(
            Drive.model,
            func.count(Drive.serial_number).label("drive_count"),
            func.count(Drive.failed_on).label("failed_count"),
            func.avg(latest.c.failure_probability).label("mean_failure_probability"),
        )
        .outerjoin(latest, latest.c.serial_number == Drive.serial_number)
        .group_by(Drive.model)
        .order_by(Drive.model)
    )
    result = await session.execute(stmt)
    return [
        {
            "model": r.model,
            "drive_count": r.drive_count,
            "failed_count": r.failed_count,
            "mean_failure_probability": round(float(r.mean_failure_probability or 0.0), 4),
        }
        for r in result
    ]


async def top_risk_drives(
    session: AsyncSession,
    limit: int = 10,
    model: str | None = None,
    min_probability: float = 0.0,
) -> list[Row]:
    latest = _latest_predictions().subquery()
    stmt = (
        select(
            Drive.serial_number,
            Drive.model,
            Drive.datacenter,
            Drive.failed_on,
            latest.c.failure_probability,
            latest.c.horizon_days,
            latest.c.model_version,
            latest.c.scored_on,
        )
        .join(latest, latest.c.serial_number == Drive.serial_number)
        .where(latest.c.failure_probability >= min_probability)
        .order_by(latest.c.failure_probability.desc(), Drive.serial_number)
        .limit(max(1, min(limit, 100)))
    )
    if model:
        stmt = stmt.where(Drive.model == model)
    result = await session.execute(stmt)
    return [
        {
            "serial_number": r.serial_number,
            "model": r.model,
            "datacenter": r.datacenter,
            "failed_on": r.failed_on.isoformat() if r.failed_on else None,
            "failure_probability": round(r.failure_probability, 4),
            "horizon_days": r.horizon_days,
            "model_version": r.model_version,
            "scored_on": r.scored_on.isoformat(),
        }
        for r in result
    ]


async def smart_history(session: AsyncSession, serial_number: str, days: int = 30) -> list[Row]:
    """SMART readings for one drive over the last ``days`` days of its recorded history."""
    last_day = await session.scalar(
        select(func.max(SmartReading.observed_on)).where(
            SmartReading.serial_number == serial_number
        )
    )
    if last_day is None:
        return []
    since = last_day - timedelta(days=max(1, min(days, 365)) - 1)
    stmt = (
        select(SmartReading)
        .where(SmartReading.serial_number == serial_number, SmartReading.observed_on >= since)
        .order_by(SmartReading.observed_on)
    )
    readings = (await session.scalars(stmt)).all()
    return [
        {
            "observed_on": r.observed_on.isoformat(),
            "power_on_hours": r.power_on_hours,
            "reallocated_sectors": r.reallocated_sectors,
            "reported_uncorrectable": r.reported_uncorrectable,
            "command_timeouts": r.command_timeouts,
            "pending_sectors": r.pending_sectors,
            "offline_uncorrectable": r.offline_uncorrectable,
            "temperature_c": r.temperature_c,
        }
        for r in readings
    ]
