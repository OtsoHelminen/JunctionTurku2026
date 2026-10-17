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
from pydantic import BaseModel, Field

from data_generator import HISTORY_SIZE, DataGenerator
from db.database import add_house, connect, events_within_radius, get_house, list_houses

# Radius around a house within which weather events are considered local.
HOUSE_RADIUS_KM = 25.0

# Coordinates of the generated estate (Koivukuja 12, 00930 Helsinki, Finland).
DEFAULT_HOUSE_LAT = 60.20
DEFAULT_HOUSE_LON = 24.94

logger = logging.getLogger("data_consolidator")


class HouseCreate(BaseModel):
    """Payload for POST /app/houses."""

    user_id: str = Field(min_length=1)
    address: str = Field(min_length=1)
    latitude: float = Field(ge=-90, le=90)
    longitude: float = Field(ge=-180, le=180)
    construction_year: int | None = None
    house_type: str | None = None
    floor_area_m2: float | None = None
    number_of_floors: int | None = None
    condition: str | None = None


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
        db = connect()
        app.state.db = db
        app.state.default_house_id = add_house(
            db, gen.estate, DEFAULT_HOUSE_LAT, DEFAULT_HOUSE_LON, user_id="system"
        )
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
            db.close()
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

    @app.get("/app/simulate/storm")
    def simulate_storm() -> dict[str, Any]:
        task: asyncio.Task = app.state.task
        if task.done() and not task.cancelled() and task.exception() is not None:
            raise HTTPException(
                status_code=503, detail="Data generator failed")
        app.state.generator.force_storm(30)
        return {"status": "storm_simulation_started", "storm_events": 30}

    @app.get("/app/houses")
    def houses() -> dict[str, Any]:
        return {"houses": list_houses(app.state.db)}

    @app.post("/app/houses", status_code=201)
    def create_house(payload: HouseCreate) -> dict[str, Any]:
        estate = payload.model_dump(
            exclude={"user_id", "latitude", "longitude"})
        house_id = add_house(
            app.state.db, estate, payload.latitude, payload.longitude, payload.user_id
        )
        return {"house": get_house(app.state.db, house_id)}

    @app.get("/app/data_events/{house_id}")
    def house_data_events(house_id: int) -> dict[str, Any]:
        """Weather events within 25 km of the given house's location."""
        house = get_house(app.state.db, house_id)
        if house is None:
            raise HTTPException(status_code=404, detail="House not found")
        events = events_within_radius(
            app.state.generator.latest(HISTORY_SIZE),
            house["latitude"],
            house["longitude"],
            HOUSE_RADIUS_KM,
        )
        return {"house": house, "radius_km": HOUSE_RADIUS_KM, "data_events": events}

    return app


app = create_app()
