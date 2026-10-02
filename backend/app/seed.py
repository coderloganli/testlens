"""Deterministic synthetic sample of drive telemetry and prediction scores.

Run with ``python -m app.seed`` against the configured DATABASE_URL.
"""

import asyncio
import random
from datetime import date, timedelta

from sqlalchemy import delete
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.db import create_engine, create_sessionmaker
from app.models import Drive, FailurePrediction, SmartReading

DRIVE_MODELS = {
    "ST12000NM0008": 12_000_138_625_024,
    "HUH721212ALN604": 12_000_138_625_024,
    "WUH721816ALE6L4": 16_000_900_661_248,
}
DATACENTERS = ["dc-east-1", "dc-west-1"]
SAMPLE_END = date(2026, 6, 30)
HISTORY_DAYS = 30
SCORE_WEEKS = 4
MODEL_VERSION = "failsight-sample-v0"


def build_sample(
    drives_per_model: int = 8, seed: int = 7
) -> tuple[list[Drive], list[SmartReading | FailurePrediction]]:
    """Return (drives, child rows). Roughly a quarter of drives degrade over the window."""
    rng = random.Random(seed)
    drives: list[Drive] = []
    children: list[SmartReading | FailurePrediction] = []
    for model_index, (model, capacity) in enumerate(DRIVE_MODELS.items()):
        for i in range(drives_per_model):
            serial = f"{model[:4]}-{model_index}{i:03d}"
            degrading = rng.random() < 0.25
            failed = degrading and rng.random() < 0.5
            drives.append(
                Drive(
                    serial_number=serial,
                    model=model,
                    capacity_bytes=capacity,
                    datacenter=rng.choice(DATACENTERS),
                    deployed_on=SAMPLE_END - timedelta(days=rng.randint(200, 1500)),
                    failed_on=SAMPLE_END - timedelta(days=rng.randint(0, 3)) if failed else None,
                )
            )

            hours = rng.randint(5_000, 35_000)
            reallocated = pending = uncorrectable = 0
            for day in range(HISTORY_DAYS):
                if degrading and day > HISTORY_DAYS // 2:
                    reallocated += rng.randint(0, 12)
                    pending += rng.randint(0, 4)
                    uncorrectable += rng.randint(0, 2)
                children.append(
                    SmartReading(
                        serial_number=serial,
                        observed_on=SAMPLE_END - timedelta(days=HISTORY_DAYS - 1 - day),
                        power_on_hours=hours + 24 * day,
                        reallocated_sectors=reallocated,
                        reported_uncorrectable=uncorrectable,
                        command_timeouts=rng.randint(0, 2),
                        pending_sectors=pending,
                        offline_uncorrectable=pending // 2,
                        temperature_c=rng.randint(28, 44),
                    )
                )

            for week in range(SCORE_WEEKS):
                base, trend = (0.45, 0.12) if degrading else (0.02, 0.0)
                probability = min(0.99, base + week * trend + rng.random() * 0.05)
                children.append(
                    FailurePrediction(
                        serial_number=serial,
                        scored_on=SAMPLE_END - timedelta(days=7 * (SCORE_WEEKS - 1 - week)),
                        model_version=MODEL_VERSION,
                        horizon_days=30,
                        failure_probability=round(probability, 4),
                    )
                )
    return drives, children


async def seed(session: AsyncSession) -> int:
    """Replace all test data with the synthetic sample. Returns the number of rows inserted."""
    for table in (FailurePrediction, SmartReading, Drive):
        await session.execute(delete(table))
    drives, children = build_sample()
    session.add_all(drives)
    await session.flush()
    session.add_all(children)
    await session.commit()
    return len(drives) + len(children)


async def main() -> None:
    engine = create_engine(get_settings().database_url)
    async with create_sessionmaker(engine)() as session:
        count = await seed(session)
    await engine.dispose()
    print(f"Seeded {count} rows")


if __name__ == "__main__":
    asyncio.run(main())
