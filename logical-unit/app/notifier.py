"""Push-ilmoitukset Appiin: hälytystapahtumat lähetetään Data Consolidatorin kautta Expoon.

  POST {CONSOLIDATOR_URL}/app/notify   {"title", "body", "sound", "data"}

Lähettäjä lukee alert_events-taulua kursorilla (notifier_state), joten mitään ei katoa:
jos consolidator ei vastaa, kursori ei etene ja tapahtuma yritetään uudelleen seuraavalla
kierroksella. Pysyvästi epäonnistuva tapahtuma ohitetaan NOTIFY_MAX_ATTEMPTS yrityksen jälkeen,
jottei se tuki jonoa.

App tunnistaa ilmoituksen data-kentästä: {"kind": "alert", "alert_id": ..., "event_type": ...}.
"""

from __future__ import annotations

import asyncio
import logging
from typing import Any

import httpx

from . import repository as repo
from .config import Settings
from .db import connect, transaction

log = logging.getLogger(__name__)

SEVERITY_FI = {
    "info": "Tiedote", "low": "Vähäinen", "medium": "Kohtalainen", "high": "Vakava", "critical": "Kriittinen",
}
TITLES = {
    "created": "{severity} hälytys – {area}",
    "escalated": "Hälytys paheni: {severity} – {area}",
    "changed": "Hälytys muuttui – {area}",
    "reminder": "Muistutus: hälytys jatkuu – {area}",
    "resolved": "Tilanne ohi – {area}",
    "analyzed": "Toimenpidesuositus – {area}",
}


def build_notification(event: dict[str, Any]) -> dict[str, Any]:
    """Tapahtuma -> consolidatorin NotificationPayload. data pidetään pienenä (Expon raja 4 kt)."""
    alert = event["alert"]
    analysis = alert.get("analysis") or {}
    event_type = event["event_type"]
    title = TITLES.get(event_type, "Hälytys – {area}").format(
        severity=SEVERITY_FI.get(alert["severity"], alert["severity"]),
        area=alert.get("area") or alert["source_id"],
    )
    expert = analysis.get("suggested_expert") or None
    body = alert["message"]
    if event_type == "analyzed" and analysis.get("recommendation"):
        body = analysis["recommendation"]
        if expert:
            price = expert["price_estimate"]
            body += f"\nSuggested expert: {expert['profession']}, approx. {price['min_eur']}–{price['max_eur']} €"
    house_id = alert["source_id"].removeprefix("house-")
    return {
        "title": title,
        "body": body[:500],
        "sound": "default" if event_type != "resolved" else None,
        "data": {
            "kind": "alert",
            "event_id": event["event_id"],
            "event_type": event_type,
            "alert_id": alert["alert_id"],
            "fingerprint": alert["fingerprint"],
            "rule_id": alert["rule_id"],
            "source_id": alert["source_id"],
            "house_id": int(house_id) if house_id.isdigit() else None,
            "area": alert.get("area"),
            "severity": alert["severity"],
            "category": alert.get("category"),
            "status": alert["status"],
            "message": alert["message"][:300],
            "recommendation": (analysis.get("recommendation") or "")[:500] or None,
            "urgency": analysis.get("urgency"),
            "expert": {
                "registered": expert["registered"],
                "profession": expert["profession"],
                "example_name": expert["example_name"],
                "price_min_eur": expert["price_estimate"]["min_eur"],
                "price_max_eur": expert["price_estimate"]["max_eur"],
            } if expert else None,
            "created_at": event["created_at"],
        },
    }


def should_notify(event: dict[str, Any], settings: Settings) -> bool:
    if event["event_type"] not in settings.notify_events:
        return False
    # Analyysi kuitatulle hälytykselle on vanhentunutta tietoa.
    return not (event["event_type"] == "analyzed" and event["alert"]["status"] != "active")


class Notifier:
    def __init__(self, settings: Settings, transport: httpx.BaseTransport | None = None) -> None:
        self.settings = settings
        self.transport = transport
        self._failures: dict[int, int] = {}  # event_id -> epäonnistuneet yritykset

    def run_once(self, limit: int = 50) -> int:
        """Lähettää uudet tapahtumat. Palauttaa lähetettyjen ilmoitusten määrän."""
        conn = connect(self.settings.db_path)
        try:
            with transaction(conn):
                cursor = repo.notifier_cursor(conn)
            events = repo.list_events(conn, cursor, limit)
            sent = 0
            with httpx.Client(
                base_url=self.settings.consolidator_url,
                timeout=self.settings.consolidator_timeout_seconds,
                transport=self.transport,
            ) as http:
                for event in events:
                    if should_notify(event, self.settings):
                        if not self._send(http, event):
                            break  # yritetään samasta kohdasta uudelleen
                        sent += 1
                    with transaction(conn):
                        repo.set_notifier_cursor(conn, event["event_id"])
            return sent
        finally:
            conn.close()

    def _send(self, http: httpx.Client, event: dict[str, Any]) -> bool:
        event_id = event["event_id"]
        try:
            response = http.post("/app/notify", json=build_notification(event))
            response.raise_for_status()
        except httpx.HTTPError as exc:
            attempts = self._failures.get(event_id, 0) + 1
            self._failures[event_id] = attempts
            if attempts < self.settings.notify_max_attempts:
                log.warning("ilmoitus %s epäonnistui (yritys %d): %s", event_id, attempts, exc)
                return False
            log.error("ilmoitus %s ohitettiin %d yrityksen jälkeen: %s", event_id, attempts, exc)
            self._failures.pop(event_id, None)
            return True  # ohitetaan, ettei jono tukkeudu
        self._failures.pop(event_id, None)
        log.info("ilmoitus lähetetty: %s %s (%s laitteelle)",
                 event["event_type"], event["alert"]["fingerprint"], response.json().get("sent"))
        return True


async def run_notifier(settings: Settings, stop: asyncio.Event) -> None:
    notifier = Notifier(settings)
    log.info("push-ilmoitukset: %s/app/notify, tapahtumat %s",
             settings.consolidator_url, ", ".join(sorted(settings.notify_events)))
    while not stop.is_set():
        try:
            await asyncio.to_thread(notifier.run_once)
        except Exception:
            log.exception("ilmoitusten lähetys epäonnistui")
        try:
            await asyncio.wait_for(stop.wait(), timeout=settings.notify_seconds)
        except asyncio.TimeoutError:
            pass
