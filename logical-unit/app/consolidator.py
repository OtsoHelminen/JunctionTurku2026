"""Data Consolidatorin datan haku ja muunnos Logical Unitin mittareiksi.

Consolidator ei lähetä dataa itse, vaan tarjoaa sen GET-rajapinnassa. Siksi Logical Unit
hakee joka minuutti:

  GET {CONSOLIDATOR_URL}/app/houses                   seurattavat kohteet
  GET {CONSOLIDATOR_URL}/app/data_events/{house_id}   kohteen lähialueen säätapahtumat

Jokaisesta kohteesta tallennetaan uusimman lähialueen tapahtuman ennuste mittareina
(source_id = "house-<id>"). Sääntömoottori käsittelee niitä kuten mitä tahansa aikasarjaa.
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
    return {
        "rain_today_mm": today.rainfall_mm,
        "wind_today_m_s": today.wind.speed_m_s,
        "temp_min_today_c": today.temperature.min_c,
        "temp_max_today_c": today.temperature.max_c,
        "rain_forecast_total_mm": round(sum(d.rainfall_mm for d in days), 2),
        "wind_forecast_max_m_s": max(d.wind.speed_m_s for d in days),
        "temp_forecast_min_c": min(d.temperature.min_c for d in days),
    }


def estate_info(payload: HouseEvents) -> dict[str, Any]:
    """Kohteen perustiedot agentille: consolidatorin house-rivi + tapahtuman estate-osa."""
    info = payload.house.model_dump(exclude={"id", "latitude", "longitude"}, exclude_none=True)
    if payload.data_events and payload.data_events[0].estate:
        info.update(payload.data_events[0].estate)
    return info


def ingest(conn: sqlite3.Connection, payload: HouseEvents, now: int) -> int:
    """Tallentaa kohteen uusimman tapahtuman. Palauttaa tallennettujen lukemien määrän.

    Jos lähialueelta ei ole tapahtumia, mitään ei tallenneta, joten no_data-sääntö huomaa katkon.
    """
    if not payload.data_events:
        return 0
    source_id = source_id_for(payload.house.id)
    repo.upsert_source(
        conn, source_id, area_from_address(payload.house.address), now,
        estate=json.dumps(estate_info(payload), ensure_ascii=False),
    )
    return repo.insert_readings(conn, source_id, now, event_metrics(payload.data_events[0]))


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
        return sum(ingest(conn, p, now) for p in payloads)


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
