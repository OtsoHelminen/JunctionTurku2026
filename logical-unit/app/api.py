"""HTTP-rajapinta.

  POST /input            Data Consolidatorin kohdedata käsin (sama muoto kuin GET /app/data_events/{id});
                         normaalisti data haetaan automaattisesti (app/consolidator.py)
  GET  /health           terveystarkistus
  GET  /alerts           hälytysten nykytila   } valinnainen lukurajapinta Appille, jos se ei
  GET  /alerts/{id}      yksittäinen hälytys   } lue SQLite-tiedostoa suoraan
  GET  /events           hälytysvirta kursorilla (after_id)
  POST /admin/evaluate   aja täysi arviointi heti (vain kun ENABLE_ADMIN_ENDPOINTS=true)
"""

from __future__ import annotations

import time
from datetime import datetime, timezone
from typing import Any, Literal

from fastapi import APIRouter, Body, HTTPException, Query, Request

from . import repository as repo
from .config import Settings
from .db import connect, session
from .consolidator import ingest
from .jobs import hourly_evaluation, purge
from .models import HouseEvents
from .serializers import alert_to_dict

router = APIRouter()

MAX_BATCH = 1000


def _settings(request: Request) -> Settings:
    return request.app.state.settings


@router.post("/input", status_code=202)
def receive_input(request: Request, body: HouseEvents | list[HouseEvents] = Body(...)) -> dict[str, Any]:
    settings = _settings(request)
    payloads = body if isinstance(body, list) else [body]
    if len(payloads) > MAX_BATCH:
        raise HTTPException(413, f"enintään {MAX_BATCH} kohdetta kerralla")
    now = int(time.time())  # consolidatorin tapahtumissa ei ole aikaleimaa
    with session(settings.db_path) as conn:  # koko erä yhtenä transaktiona
        accepted = sum(ingest(conn, payload, now) for payload in payloads)
    return {"accepted_readings": accepted, "houses_without_events": sum(not p.data_events for p in payloads)}


@router.get("/health")
def health(request: Request) -> dict[str, Any]:
    settings = _settings(request)
    conn = connect(settings.db_path)
    try:
        conn.execute("SELECT 1").fetchone()
    finally:
        conn.close()
    return {
        "status": "ok",
        "rules": len(request.app.state.rules),
        "agent_enabled": settings.agent_enabled,
        "model": settings.llm_model if settings.agent_enabled else None,
    }


@router.get("/alerts")
def list_alerts(
    request: Request,
    status: Literal["active", "resolved", "all"] = "active",
    updated_after: datetime | None = None,
    limit: int = Query(100, ge=1, le=500),
) -> dict[str, Any]:
    after = None
    if updated_after is not None:
        if updated_after.tzinfo is None:
            updated_after = updated_after.replace(tzinfo=timezone.utc)
        after = int(updated_after.timestamp())
    conn = connect(_settings(request).db_path)
    try:
        return {"alerts": repo.list_alerts(conn, status, after, limit)}
    finally:
        conn.close()


@router.get("/alerts/{alert_id}")
def get_alert(request: Request, alert_id: int) -> dict[str, Any]:
    conn = connect(_settings(request).db_path)
    try:
        row = repo.get_alert(conn, alert_id)
    finally:
        conn.close()
    if row is None:
        raise HTTPException(404, "hälytystä ei löydy")
    return alert_to_dict(row)


@router.get("/events")
def list_events(
    request: Request,
    after_id: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
) -> dict[str, Any]:
    conn = connect(_settings(request).db_path)
    try:
        events = repo.list_events(conn, after_id, limit)
    finally:
        conn.close()
    return {"events": events, "last_id": events[-1]["event_id"] if events else after_id}


@router.post("/admin/evaluate")
def admin_evaluate(request: Request) -> dict[str, Any]:
    settings = _settings(request)
    if not settings.admin_endpoints:
        raise HTTPException(404, "Not Found")
    now = int(time.time())
    purge(settings, now)
    events = hourly_evaluation(settings, request.app.state.rules, now)
    return {"events": events}
