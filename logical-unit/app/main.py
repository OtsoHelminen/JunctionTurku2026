"""Sovelluksen käynnistys: tietokanta, säännöt, ajastin ja agentti.

Aja YHDELLÄ prosessilla (uvicorn ilman --workers > 1), muuten ajastin käynnistyy moneen kertaan.
"""

from __future__ import annotations

import asyncio
import logging
import os
from contextlib import asynccontextmanager

from fastapi import FastAPI

from .agent.llm import OpenAICompatibleClient
from .agent.worker import run_agent_worker
from .api import router
from .config import load_settings
from .db import init_db
from .jobs import run_scheduler
from .rules import load_rules, validate_against_retention
from .seed import seed_if_empty

log = logging.getLogger("logical_unit")


def create_app() -> FastAPI:
    @asynccontextmanager
    async def lifespan(app: FastAPI):
        logging.basicConfig(
            level=os.getenv("LOG_LEVEL", "INFO"),
            format="%(asctime)s %(levelname)s %(name)s: %(message)s",
        )
        settings = load_settings()
        init_db(settings.db_path)
        rules = load_rules(settings.rules_path)
        validate_against_retention(rules, settings.retention_minutes)
        seed_if_empty(settings)

        client = (
            OpenAICompatibleClient(
                settings.llm_base_url, settings.llm_model, settings.llm_api_key, settings.llm_timeout_seconds
            )
            if settings.agent_enabled
            else None
        )
        app.state.settings = settings
        app.state.rules = rules

        stop = asyncio.Event()
        tasks: list[asyncio.Task] = []
        if settings.scheduler_enabled:
            tasks.append(asyncio.create_task(run_scheduler(settings, rules, stop), name="scheduler"))
            tasks.append(asyncio.create_task(run_agent_worker(settings, client, stop), name="agent-worker"))
        log.info(
            "Logical Unit käynnissä: %d sääntöä, kanta %s, agentti %s",
            len(rules), settings.db_path, settings.llm_model if client else "pois päältä",
        )
        try:
            yield
        finally:
            stop.set()
            if tasks:
                _, pending = await asyncio.wait(tasks, timeout=10)
                for task in pending:
                    task.cancel()

    app = FastAPI(title="Logical Unit", version="0.1.0", lifespan=lifespan)
    app.include_router(router)
    return app


app = create_app()
