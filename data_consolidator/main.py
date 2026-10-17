"""FastAPI server exposing generated data events.

Run:  DATA_INTERVAL_SECONDS=60 uvicorn main:app --reload
"""

from __future__ import annotations

import asyncio
import logging
import os
from contextlib import asynccontextmanager
from typing import Any

from fastapi import FastAPI, HTTPException

from data_generator import HISTORY_SIZE, DataGenerator

logger = logging.getLogger("data_consolidator")


def get_interval() -> float:
    raw = os.environ.get("DATA_INTERVAL_SECONDS", "60")
    try:
        value = float(raw)
    except ValueError as exc:
        raise RuntimeError(
            f"DATA_INTERVAL_SECONDS must be a number, got {raw!r}") from exc
    if value <= 0:
        raise RuntimeError("DATA_INTERVAL_SECONDS must be > 0")
    return value


async def _generate_loop(gen: DataGenerator, interval: float) -> None:
    while True:
        await asyncio.sleep(interval)
        gen.generate_event()


def create_app(interval: float | None = None, seed: int | None = None) -> FastAPI:
    @asynccontextmanager
    async def lifespan(app: FastAPI):
        period = interval if interval is not None else get_interval()
        gen = DataGenerator(seed=seed)
        gen.initialize_history(HISTORY_SIZE)
        app.state.generator = gen
        task = asyncio.create_task(_generate_loop(gen, period))

        def _on_done(t: asyncio.Task) -> None:
            if not t.cancelled() and t.exception() is not None:
                logger.error("Background generator stopped",
                             exc_info=t.exception())

        task.add_done_callback(_on_done)
        app.state.task = task
        try:
            yield
        finally:
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass

    app = FastAPI(title="Data Consolidator", lifespan=lifespan)

    @app.get("/app/data_events")
    def data_events() -> dict[str, Any]:
        task: asyncio.Task = app.state.task
        if task.done() and not task.cancelled() and task.exception() is not None:
            raise HTTPException(
                status_code=503, detail="Data generator failed")
        events = app.state.generator.latest(HISTORY_SIZE)
        if len(events) != HISTORY_SIZE:
            raise HTTPException(
                status_code=503, detail="Event history incomplete")
        return {"data_events": events}

    return app


app = create_app()
