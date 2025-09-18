import asyncio
import logging
from datetime import datetime

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.data import models, repositories
from app.utils.logging import setup_logging
from app.utils.run_logs import capture_run_logs


def test_capture_run_logs_collects_entries():
    setup_logging()
    logger = logging.getLogger("market_aggregator.test")
    with capture_run_logs() as entries:
        logger.info("hello world")
        try:
            raise ValueError("boom")
        except ValueError:
            logger.exception("failure recorded")

    assert len(entries) == 2
    assert entries[0]["message"].endswith("hello world")
    assert entries[1]["level"] == "ERROR"
    assert entries[1]["exception"] is not None and "ValueError" in entries[1]["exception"]

def test_store_and_fetch_run_logs():
    async def _run() -> None:
        engine = create_async_engine("sqlite+aiosqlite:///:memory:")
        async_session = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)

        async with engine.begin() as conn:
            await conn.run_sync(models.Base.metadata.create_all)

        async with async_session() as session:
            newsletter = models.Newsletter(
                slug="test",
                name="Test",
                timezone="UTC",
                schedule_times=["06:00"],
                include_watchlist=False,
                custom_prompt="",
            )
            session.add(newsletter)
            await session.flush()

            run = models.RunRecord(newsletter_id=newsletter.id)
            session.add(run)
            await session.flush()

            payload = [
                {
                    "timestamp": datetime.utcnow(),
                    "level": "INFO",
                    "logger": "market_aggregator.test",
                    "message": "first",
                    "exception": None,
                },
                {
                    "timestamp": datetime.utcnow(),
                    "level": "ERROR",
                    "logger": "market_aggregator.test",
                    "message": "second",
                    "exception": "Traceback...",
                },
            ]
            await repositories.append_run_logs(session, run_id=run.id, entries=payload)
            fetched = await repositories.list_run_logs(session, run_id=run.id, limit=10)
            assert [entry.message for entry in fetched] == [item["message"] for item in payload]
            total = await repositories.count_run_logs(session, run_id=run.id)
            assert total == len(payload)

        await engine.dispose()

    asyncio.run(_run())
