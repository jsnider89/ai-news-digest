"""Prepare database and configuration defaults before the app starts."""
from __future__ import annotations

import asyncio
import logging

from app.ai.pipeline import dump_default_pipeline
from app.config.settings import get_settings
from app.data.database import init_db
from app.utils.logging import setup_logging


async def _prepare() -> None:
    settings = get_settings()
    dump_default_pipeline()
    await init_db()
    logging.getLogger(__name__).info("Database initialised at %s", settings.database_url)


def main() -> None:
    setup_logging()
    asyncio.run(_prepare())


if __name__ == "__main__":
    main()

