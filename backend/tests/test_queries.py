from app import queries
from app.seed import DRIVE_MODELS, HISTORY_DAYS, build_sample


async def test_fleet_summary_covers_every_model(sessionmaker):
    async with sessionmaker() as session:
        rows = await queries.fleet_summary(session)
    drives, _ = build_sample()
    assert [r["model"] for r in rows] == sorted(DRIVE_MODELS)
    assert sum(r["drive_count"] for r in rows) == len(drives)
    assert sum(r["failed_count"] for r in rows) == sum(d.failed_on is not None for d in drives)


async def test_top_risk_drives_uses_latest_score_and_sorts_descending(sessionmaker):
    async with sessionmaker() as session:
        rows = await queries.top_risk_drives(session, limit=5)
    probabilities = [r["failure_probability"] for r in rows]
    assert len(rows) == 5
    assert probabilities == sorted(probabilities, reverse=True)
    assert len({r["scored_on"] for r in rows}) == 1


async def test_top_risk_drives_filters(sessionmaker):
    model = next(iter(DRIVE_MODELS))
    async with sessionmaker() as session:
        rows = await queries.top_risk_drives(session, limit=100, model=model, min_probability=0.3)
    assert rows
    assert all(r["model"] == model and r["failure_probability"] >= 0.3 for r in rows)


async def test_smart_history_window(sessionmaker):
    serial = build_sample()[0][0].serial_number
    async with sessionmaker() as session:
        full = await queries.smart_history(session, serial, days=365)
        week = await queries.smart_history(session, serial, days=7)
        missing = await queries.smart_history(session, "NOPE-0000")
    assert len(full) == HISTORY_DAYS
    assert week == full[-7:]
    assert missing == []
