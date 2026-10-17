"""Ajastetut työt.

  minuuttiajo:  tiivistä + poista yli RETENTION_MINUTES vanha raakadata,
                arvioi immediate-säännöt (kriittiset tilanteet heti)
  tuntiajo:     arvioi kaikki säännöt kaikille lähteille, luo/päivitä/kuittaa hälytykset

Funktiot ottavat ajan parametrina, joten niitä voi testata ja simuloida ilman odottelua.
"""

from __future__ import annotations

import asyncio
import logging
import time
from typing import Any

from . import repository as repo
from .config import Settings
from .db import session
from .lifecycle import reconcile_source
from .rules import Rule, Window, evaluate

log = logging.getLogger(__name__)


def purge(settings: Settings, now: int) -> int:
    with session(settings.db_path) as conn:
        return repo.compact_and_purge(
            conn,
            cutoff=now - settings.retention_minutes * 60,
            summary_cutoff=now - settings.summary_retention_days * 86400,
        )


def evaluate_all(settings: Settings, rules: list[Rule], now: int, *, full: bool) -> list[dict[str, Any]]:
    selected = rules if full else [r for r in rules if r.immediate]
    if not selected:
        return []
    since = now - max((r.history_minutes for r in selected), default=0) * 60
    events: list[dict[str, Any]] = []
    with session(settings.db_path) as conn:
        for source in repo.list_sources(conn):
            source_id = source["source_id"]
            applicable = [r for r in selected if r.applies_to(source_id)]
            window = Window(
                source_id=source_id,
                now=now,
                series=repo.load_window(conn, source_id, since, now),
                last_seen=source["last_seen"],
            )
            events += reconcile_source(
                conn,
                source_id=source_id,
                area=source["area"],
                outcomes=[evaluate(rule, window) for rule in applicable],
                now=now,
                settings=settings,
                full=full,
            )
    return events


def minute_tick(settings: Settings, rules: list[Rule], now: int) -> list[dict[str, Any]]:
    deleted = purge(settings, now)
    events = evaluate_all(settings, rules, now, full=False)
    if deleted or events:
        log.info("minute tick: purged %d readings, %d events", deleted, len(events))
    return events


def hourly_evaluation(settings: Settings, rules: list[Rule], now: int) -> list[dict[str, Any]]:
    events = evaluate_all(settings, rules, now, full=True)
    log.info("full evaluation: %d events", len(events))
    for event in events:
        alert = event["alert"]
        log.info("  %s %s [%s] %s", event["event_type"], alert["fingerprint"], alert["severity"], alert["message"])
    return events


def next_boundary(now: int, interval_seconds: int) -> int:
    """Seuraava tasaväli, esim. seuraava tasatunti."""
    return (now // interval_seconds + 1) * interval_seconds


async def run_scheduler(settings: Settings, rules: list[Rule], stop: asyncio.Event) -> None:
    interval = settings.evaluation_interval_minutes * 60
    next_eval = next_boundary(int(time.time()), interval)
    log.info("scheduler running, next full evaluation %s", time.strftime("%H:%M:%S", time.localtime(next_eval)))
    while not stop.is_set():
        now = int(time.time())
        try:
            await asyncio.to_thread(minute_tick, settings, rules, now)
            if now >= next_eval:
                await asyncio.to_thread(hourly_evaluation, settings, rules, now)
                next_eval = next_boundary(now, interval)
        except Exception:  # ajastin ei saa kaatua yksittäiseen virheeseen
            log.exception("scheduled job failed")
        try:
            await asyncio.wait_for(stop.wait(), timeout=settings.tick_seconds)
        except asyncio.TimeoutError:
            pass
