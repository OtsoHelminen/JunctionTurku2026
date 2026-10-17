"""Data Consolidatorin datan haku ja muunnos Logical Unitin mittareiksi.

Consolidator ei lähetä dataa itse, vaan tarjoaa sen GET-rajapinnassa. Siksi Logical Unit
hakee joka minuutti:

  GET {CONSOLIDATOR_URL}/app/houses                   seurattavat kohteet
  GET {CONSOLIDATOR_URL}/app/data_events/{house_id}   kohteen lähialueen säätapahtumat

Vastauksessa on kohteen viimeisen tunnin tapahtumat (yksi minuutissa). Jokainen tallennetaan
omalla aikaleimallaan mittareina (source_id = "house-<id>"); sama aikaleima uudestaan vain
päivittää rivin, joten haun katkettua puuttuvat minuutit täydentyvät seuraavalla haulla.
Sääntömoottori käsittelee mittareita kuten mitä tahansa aikasarjaa.
"""

from __future__ import annotations

import asyncio
import json
import logging
import re
import sqlite3
import time
from typing import Any

import httpx
from pydantic import ValidationError

from . import repository as repo
from .config import Settings
from .db import session
from .models import DataEvent, HouseEvents

log = logging.getLogger(__name__)

_POSTCODE_RE = re.compile(r"^\d{5}\s+")

# Consolidatorin ääri-ilmiöt mittareiksi: 0 = ei varoitusta, 1 = warning, 2 = severe.
EXTREME_METRICS = {"flood": "flood_level", "forest_fire": "forest_fire_level"}
EXTREME_LEVELS = {"warning": 1.0, "severe": 2.0}
# Kohteen tietokantarivin kentät, joista ei ole hyötyä agentille.
_ESTATE_SKIP = {"id", "user_id", "latitude", "longitude", "created_at"}


def source_id_for(house_id: int) -> str:
    return f"house-{house_id}"


def area_from_address(address: str) -> str | None:
    """'Koivukuja 12, 00930 Helsinki, Finland' -> 'Helsinki' (ratkaisijoiden alue)."""
    parts = [p.strip() for p in address.split(",") if p.strip()]
    if len(parts) < 2:
        return None
    city = parts[-2] if len(parts) >= 3 else parts[-1]
    return _POSTCODE_RE.sub("", city) or None


def event_metrics(event: DataEvent) -> dict[str, float]:
    """Ennuste -> mittarit. Päivä 0 = tämä päivä, koko ennuste = tulevat päivät (yleensä 3)."""
    days = event.weather.forecast
    today = days[0]
    metrics = {
        "rain_today_mm": today.rainfall_mm,
        "wind_today_m_s": today.wind.speed_m_s,
        "temp_min_today_c": today.temperature.min_c,
        "temp_max_today_c": today.temperature.max_c,
        "rain_forecast_total_mm": round(sum(d.rainfall_mm for d in days), 2),
        "wind_forecast_max_m_s": max(d.wind.speed_m_s for d in days),
        "temp_forecast_min_c": min(d.temperature.min_c for d in days),
    }
    for metric in EXTREME_METRICS.values():  # 0 aina mukana, jotta hälytys kuittautuu
        metrics[metric] = 0.0
    for extreme in event.extremes:
        metric = EXTREME_METRICS.get(extreme.type)
        if metric:
            metrics[metric] = max(metrics[metric], EXTREME_LEVELS.get(extreme.severity, 1.0))
    return metrics


def estate_info(payload: HouseEvents) -> dict[str, Any]:
    """Kohteen perustiedot agentille: consolidatorin house-rivi + tapahtuman estate-osa."""
    info = payload.house.model_dump(exclude=_ESTATE_SKIP, exclude_none=True)
    if payload.data_events and payload.data_events[0].estate:
        info.update({k: v for k, v in payload.data_events[0].estate.items() if k not in _ESTATE_SKIP and v is not None})
    return info


def ingest(conn: sqlite3.Connection, payload: HouseEvents, now: int, settings: Settings) -> int:
    """Tallentaa kohteen tapahtumat. Palauttaa tallennettujen lukemien määrän.

    Säilytysikkunaa vanhemmat ja yli MAX_FUTURE_SKEW_SECONDS tulevaisuudessa olevat ohitetaan.
    Jos kelvollisia tapahtumia ei ole, mitään ei tallenneta, joten no_data-sääntö huomaa katkon.
    """
    oldest = now - settings.retention_minutes * 60
    newest = now + settings.max_future_skew_seconds
    events = [(event.epoch(now), event) for event in payload.data_events]
    events = [(ts, event) for ts, event in events if oldest <= ts <= newest]
    skipped = len(payload.data_events) - len(events)
    if skipped:
        log.debug("kohde %s: %d tapahtumaa aikaikkunan ulkopuolella", payload.house.id, skipped)
    if not events:
        return 0
    source_id = source_id_for(payload.house.id)
    repo.upsert_source(
        conn, source_id, area_from_address(payload.house.address), max(ts for ts, _ in events),
        estate=json.dumps(estate_info(payload), ensure_ascii=False),
    )
    return sum(repo.insert_readings(conn, source_id, ts, event_metrics(event)) for ts, event in events)


def fetch_all(base_url: str, timeout: float, transport: httpx.BaseTransport | None = None) -> list[HouseEvents]:
    """Hakee kaikkien kohteiden datan. Virheellinen kohde ohitetaan, muut käsitellään."""
    result: list[HouseEvents] = []
    with httpx.Client(base_url=base_url, timeout=timeout, transport=transport) as http:
        response = http.get("/app/houses")
        response.raise_for_status()
        for house in response.json().get("houses", []):
            try:
                r = http.get(f"/app/data_events/{house['id']}")
                r.raise_for_status()
                result.append(HouseEvents.model_validate(r.json()))
            except (httpx.HTTPError, ValidationError, KeyError, ValueError) as exc:
                log.warning("kohteen %s data ohitettiin: %s", house.get("id"), exc)
    return result


def poll_once(settings: Settings, now: int) -> int:
    payloads = fetch_all(settings.consolidator_url, settings.consolidator_timeout_seconds)
    with session(settings.db_path) as conn:
        return sum(ingest(conn, p, now, settings) for p in payloads)


async def run_poller(settings: Settings, stop: asyncio.Event) -> None:
    log.info("haetaan dataa %s %d s välein", settings.consolidator_url, settings.poll_seconds)
    while not stop.is_set():
        try:
            stored = await asyncio.to_thread(poll_once, settings, int(time.time()))
            log.debug("consolidator: %d lukemaa", stored)
        except httpx.HTTPError as exc:  # consolidator alhaalla -> no_data-sääntö hälyttää
            log.warning("Data Consolidator ei vastaa: %s", exc)
        except Exception:
            log.exception("datan haku epäonnistui")
        try:
            await asyncio.wait_for(stop.wait(), timeout=settings.poll_seconds)
        except asyncio.TimeoutError:
            pass
