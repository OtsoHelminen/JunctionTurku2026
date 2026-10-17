

"""FastAPI server exposing generated data events.

Run:  DATA_INTERVAL_SECONDS=60 uvicorn main:app --reload
"""

from __future__ import annotations

import asyncio
import logging
import json
import os
import re
import urllib.request
from contextlib import asynccontextmanager
from typing import Any, Literal

from fastapi import FastAPI, HTTPException, Query, Response
from pydantic import BaseModel, Field, field_validator

from data_generator import HISTORY_SIZE, HOUSE_RADIUS_KM, DataGenerator
from db.database import (
    add_house,
    connect,
    delete_push_token,
    ensure_push_tokens_table,
    get_house,
    get_push_token,
    list_houses,
    list_push_tokens,
    upsert_push_token,
)

EXPO_PUSH_URL = "https://exp.host/--/api/v2/push/send"
EXPO_BATCH_SIZE = 100  # Expo accepts at most 100 messages per request
EXPO_TOKEN_RE = re.compile(r"^Expo(nent)?PushToken\[[^\[\]]+\]$")

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


class DeviceCreate(BaseModel):
    """Payload for POST /app/devices."""

    token: str
    platform: Literal["ios", "android"] | None = None

    @field_validator("token")
    @classmethod
    def _check_token(cls, v: str) -> str:
        v = v.strip()
        if not EXPO_TOKEN_RE.match(v):
            raise ValueError("token must look like ExponentPushToken[...]")
        return v


class NotificationPayload(BaseModel):
    """Optional body for POST /app/notify and /app/notify/{token}."""

    title: str | None = "Data updated"
    body: str | None = "New data is available."
    sound: str | None = "default"
    data: dict[str, Any] | None = None


def send_expo_push(tokens: list[str], payload: NotificationPayload) -> list[dict[str, Any]]:
    """Send one message per token to Expo; returns the push tickets in token order."""
    tickets: list[dict[str, Any]] = []
    for i in range(0, len(tokens), EXPO_BATCH_SIZE):
        messages = [
            {"to": t, **payload.model_dump(exclude_none=True)}
            for t in tokens[i: i + EXPO_BATCH_SIZE]
        ]
        req = urllib.request.Request(
            EXPO_PUSH_URL,
            data=json.dumps(messages).encode(),
            headers={
                "Accept": "application/json",
                "Accept-Encoding": "identity",
                "Content-Type": "application/json",
            },
            method="POST",
        )
        try:
            with urllib.request.urlopen(req, timeout=15) as resp:
                result = json.loads(resp.read().decode())
        except Exception as exc:  # network error or non-2xx from Expo
            logger.error("Expo push request failed", exc_info=exc)
            raise HTTPException(
                status_code=502, detail="Expo push service request failed") from exc
        tickets.extend(result.get("data", []))
    return tickets


def prune_unregistered(db, tokens: list[str], tickets: list[dict[str, Any]]) -> list[str]:
    """Delete tokens whose ticket says DeviceNotRegistered; returns the removed tokens."""
    removed = []
    for token, ticket in zip(tokens, tickets):
        if ticket.get("status") == "error" and (ticket.get("details") or {}).get("error") == "DeviceNotRegistered":
            delete_push_token(db, token)
            removed.append(token)
    return removed


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
        app.state.generator = gen
        db = connect()
        ensure_push_tokens_table(db)
        app.state.db = db
        app.state.default_house_id = add_house(
            db, gen.estate, DEFAULT_HOUSE_LAT, DEFAULT_HOUSE_LON, user_id="system"
        )
        for house in list_houses(db):
            gen.register_house(house)
        gen.initialize_history(HISTORY_SIZE)
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
            finally:
                db.close()

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
    async def create_house(payload: HouseCreate) -> dict[str, Any]:
        try:
            app.state.generator.validate_house(
                payload.latitude, payload.longitude)
        except ValueError as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc
        estate = payload.model_dump(
            exclude={"user_id", "latitude", "longitude"})
        house_id = add_house(
            app.state.db, estate, payload.latitude, payload.longitude, payload.user_id
        )
        house = get_house(app.state.db, house_id)
        if house is None:
            raise HTTPException(
                status_code=500, detail="Saved house could not be read")
        app.state.generator.register_house(house)
        return {"house": house}

    @app.get("/app/data_events/{house_id}")
    def house_data_events(house_id: int) -> dict[str, Any]:
        """Weather events within 25 km of the given house's location."""
        house = get_house(app.state.db, house_id)
        if house is None:
            raise HTTPException(status_code=404, detail="House not found")
        events = app.state.generator.latest_for_house(house_id, HISTORY_SIZE)
        return {"house": house, "radius_km": HOUSE_RADIUS_KM, "data_events": events}

    # --- Push notifications -------------------------------------------------

    @app.post("/app/devices", status_code=204)
    def register_device(payload: DeviceCreate) -> Response:
        """Register an Expo push token (re-registering only refreshes updated_at)."""
        upsert_push_token(app.state.db, payload.token, payload.platform)
        return Response(status_code=204)

    @app.delete("/app/devices", status_code=204)
    def unregister_device(token: str = Query(min_length=1)) -> Response:
        """Remove a token. Idempotent: succeeds even if the token is unknown."""
        delete_push_token(app.state.db, token)
        return Response(status_code=204)

    @app.post("/app/notify/{token}")
    def notify_token(token: str, payload: NotificationPayload | None = None) -> dict[str, Any]:
        """Send a push notification to one registered device.

        The token contains brackets, so URL-encode it:
        /app/notify/ExponentPushToken%5Bxxxx%5D
        """
        if get_push_token(app.state.db, token) is None:
            raise HTTPException(
                status_code=404, detail="Device token not registered")
        tickets = send_expo_push([token], payload or NotificationPayload())
        removed = prune_unregistered(app.state.db, [token], tickets)
        return {"sent": 1, "tickets": tickets, "removed_tokens": removed}

    @app.post("/app/notify")
    def notify_all(payload: NotificationPayload | None = None) -> dict[str, Any]:
        """Send a push notification to every registered device."""
        tokens = list_push_tokens(app.state.db)
        if not tokens:
            return {"sent": 0, "tickets": [], "removed_tokens": []}
        tickets = send_expo_push(tokens, payload or NotificationPayload())
        removed = prune_unregistered(app.state.db, tokens, tickets)
        return {"sent": len(tokens), "tickets": tickets, "removed_tokens": removed}

    return app


app = create_app()
