"""Taustatyö, joka analysoi odottavat hälytykset.

Hälytys tallennetaan aina ensin (analysis.status = pending). Agentti täydentää sen perässä,
joten hidas tai kaatunut malli ei koskaan estä hälytyksen syntymistä.
"""

from __future__ import annotations

import asyncio
import logging
import time

from .. import repository as repo
from ..config import Settings
from ..db import connect, transaction
from .analyst import analyze_alert, fallback_analysis
from .llm import ChatClient

log = logging.getLogger(__name__)


def process_pending(settings: Settings, client: ChatClient | None, now: int | None = None, limit: int = 5) -> int:
    conn = connect(settings.db_path)
    try:
        rows = repo.pending_analyses(conn, now or int(time.time()), limit)
        for row in rows:
            ts = now or int(time.time())
            if client is None:
                analysis, status = fallback_analysis(conn, row, ts, "agent_disabled"), "skipped"
            else:
                try:
                    analysis, status = analyze_alert(conn, row, client, settings, ts), "done"
                except Exception as exc:  # verkko, aikakatkaisu, kelvoton vastaus...
                    with transaction(conn):
                        attempts = repo.register_analysis_failure(conn, row["id"], ts)
                    log.warning("analysis failed (alert %s, attempt %d): %s", row["id"], attempts, exc)
                    if attempts < settings.agent_max_attempts:
                        continue
                    analysis = fallback_analysis(conn, row, ts, f"agent_failed: {type(exc).__name__}")
                    status = "failed"
            with transaction(conn):
                if repo.save_analysis(conn, row["id"], row["revision"], status, analysis, ts):
                    repo.add_event(conn, row["id"], "analyzed", ts)
        return len(rows)
    finally:
        conn.close()


async def run_agent_worker(settings: Settings, client: ChatClient | None, stop: asyncio.Event) -> None:
    while not stop.is_set():
        processed = 0
        try:
            processed = await asyncio.to_thread(process_pending, settings, client)
        except Exception:
            log.exception("analysis job failed")
        try:
            await asyncio.wait_for(stop.wait(), timeout=1 if processed else 5)
        except asyncio.TimeoutError:
            pass
