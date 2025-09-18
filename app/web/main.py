"""FastAPI application entry point."""
from __future__ import annotations

import logging
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.config.settings import get_settings
from app.data.database import init_db
from app.tasks.scheduler import scheduler
from app.utils.logging import setup_logging
from .api import (
    logs as log_routes,
    meta as meta_routes,
    newsletters,
    runs,
    settings as settings_routes,
    status as status_routes,
)

settings = get_settings()
setup_logging()
logger = logging.getLogger("market_aggregator.web")

app = FastAPI(title=settings.app_name)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Add API routes first, before static file mounting
app.include_router(status_routes.router)
app.include_router(settings_routes.router)
app.include_router(newsletters.router)
app.include_router(runs.router)
app.include_router(log_routes.router)
app.include_router(meta_routes.router)

# Mount static files after API routes
static_dir = Path(__file__).parent / "static"
index_file = static_dir / "index.html"
if static_dir.exists() and index_file.exists():
    app.mount("/", StaticFiles(directory=static_dir, html=True), name="static")
else:
    @app.get("/")
    async def index() -> dict:
        return {"message": "Aggregator API running", "docs": "/docs", "health": "/health"}


@app.on_event("startup")
async def on_startup() -> None:
    logger.info("Initialising database")
    await init_db()
    await scheduler.start()


@app.on_event("shutdown")
async def on_shutdown() -> None:
    await scheduler.shutdown()
