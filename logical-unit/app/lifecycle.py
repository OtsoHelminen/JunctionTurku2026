"""Hälytysten elinkaari: milloin luodaan uusi, milloin pysytään hiljaa, milloin kuitataan.

Tämä toteuttaa periaatteen "hälytys tulee vain, kun on jotain uutta":

  uusi tilanne                         -> created   (+ agenttianalyysi)
  vakavuus nousee                      -> escalated (+ uusi analyysi)
  vakavuus laskee / arvo muuttuu > X % -> changed   (+ uusi analyysi)   [vain täysi arviointi]
  ennallaan, muistutusväli täynnä      -> reminder                       [vain täysi arviointi]
  ennallaan                            -> ei tapahtumaa (vain last_seen päivittyy)
  ehto ei enää täyty (CLEAR)           -> resolved                       [vain täysi arviointi]
  dataa ei ole (UNKNOWN)               -> ei mitään: puuttuva data ei kuittaa hälytystä

Minuuttiajo (osittainen arviointi, vain immediate-säännöt) voi ainoastaan luoda tai eskaloida.
"""

from __future__ import annotations

import sqlite3
from collections import defaultdict
from typing import Any

from . import repository as repo
from .config import Settings
from .rules import CLEAR, FIRED, SEVERITY_ORDER, Finding, Outcome


def reconcile_source(
    conn: sqlite3.Connection,
    *,
    source_id: str,
    area: str | None,
    outcomes: list[Outcome],
    now: int,
    settings: Settings,
    full: bool,
) -> list[dict[str, Any]]:
    groups: dict[str, list[Outcome]] = defaultdict(list)
    for outcome in outcomes:
        groups[outcome.rule.fingerprint(source_id)].append(outcome)

    active = {row["fingerprint"]: row for row in repo.active_alerts_for_source(conn, source_id)}
    events: list[dict[str, Any]] = []

    for fingerprint, group in groups.items():
        fired = [o.finding for o in group if o.status == FIRED]
        if fired:
            best = max(fired, key=lambda f: SEVERITY_ORDER[f.severity])
            events.extend(_upsert(conn, active.get(fingerprint), best, area, now, settings, full))
        elif full and fingerprint in active and any(o.status == CLEAR for o in group):
            repo.resolve_alert(conn, active[fingerprint]["id"], now, "condition_cleared")
            events.append(repo.add_event(conn, active[fingerprint]["id"], "resolved", now))

    if full:
        # Sääntö poistettu tai rajattu pois tältä lähteeltä -> kuitataan.
        for fingerprint, row in active.items():
            if fingerprint not in groups:
                repo.resolve_alert(conn, row["id"], now, "rule_removed")
                events.append(repo.add_event(conn, row["id"], "resolved", now))
    return events


def _upsert(
    conn: sqlite3.Connection,
    row: sqlite3.Row | None,
    finding: Finding,
    area: str | None,
    now: int,
    settings: Settings,
    full: bool,
) -> list[dict[str, Any]]:
    if row is None:
        alert_id = repo.insert_alert(conn, finding, area, now)
        return [repo.add_event(conn, alert_id, "created", now)]

    old_rank = SEVERITY_ORDER[row["severity"]]
    new_rank = SEVERITY_ORDER[finding.severity]

    if new_rank > old_rank:
        repo.update_alert(conn, row["id"], finding, now)
        return [repo.add_event(conn, row["id"], "escalated", now)]

    if not full:
        repo.touch_alert(conn, row["id"], now)
        return []

    value_changed = finding.rule.notify_on_value_change and _significant_change(
        row["value"], finding.value, settings.change_threshold_pct
    )
    if new_rank < old_rank or value_changed:
        repo.update_alert(conn, row["id"], finding, now)
        return [repo.add_event(conn, row["id"], "changed", now)]

    if now - row["last_notified"] >= settings.renotify_hours * 3600:
        repo.mark_reminded(conn, row["id"], now)
        return [repo.add_event(conn, row["id"], "reminder", now)]

    repo.touch_alert(conn, row["id"], now)
    return []


def _significant_change(old: float | None, new: float | None, threshold_pct: float) -> bool:
    """Verrataan edellisen ILMOITUKSEN arvoon, joten hidas ajautuminenkin huomataan lopulta."""
    if old is None or new is None:
        return False
    if old == 0:
        return new != 0
    return abs(new - old) / abs(old) * 100 >= threshold_pct
