"""Kaikki SQL-kyselyt yhdessä paikassa."""

from __future__ import annotations

import json
import sqlite3
from collections import defaultdict
from typing import Any

from .rules import Finding
from .serializers import alert_to_dict, iso

SEVERITY_SQL = (
    "CASE severity WHEN 'critical' THEN 4 WHEN 'high' THEN 3 WHEN 'medium' THEN 2 "
    "WHEN 'low' THEN 1 ELSE 0 END"
)


# ---------------------------------------------------------------- lähteet ja lukemat

def upsert_source(conn: sqlite3.Connection, source_id: str, area: str | None, ts: int) -> None:
    conn.execute(
        """
        INSERT INTO sources (source_id, area, first_seen, last_seen) VALUES (?, ?, ?, ?)
        ON CONFLICT (source_id) DO UPDATE SET
            area = COALESCE(excluded.area, sources.area),
            last_seen = MAX(sources.last_seen, excluded.last_seen)
        """,
        (source_id, area, ts, ts),
    )


def insert_readings(conn: sqlite3.Connection, source_id: str, ts: int, metrics: dict[str, float]) -> int:
    # Sama (lähde, mittari, aikaleima) uudestaan = päivitys, ei tuplariviä (idempotentti).
    conn.executemany(
        """
        INSERT INTO readings (source_id, metric, ts, value) VALUES (?, ?, ?, ?)
        ON CONFLICT (source_id, metric, ts) DO UPDATE SET value = excluded.value
        """,
        [(source_id, metric, ts, float(value)) for metric, value in metrics.items()],
    )
    return len(metrics)


def list_sources(conn: sqlite3.Connection) -> list[sqlite3.Row]:
    return conn.execute("SELECT * FROM sources ORDER BY source_id").fetchall()


def load_window(conn: sqlite3.Connection, source_id: str, since: int, now: int) -> dict[str, list[tuple[int, float]]]:
    series: dict[str, list[tuple[int, float]]] = defaultdict(list)
    rows = conn.execute(
        "SELECT metric, ts, value FROM readings WHERE source_id = ? AND ts BETWEEN ? AND ? ORDER BY ts",
        (source_id, since, now),
    )
    for row in rows:
        series[row["metric"]].append((row["ts"], row["value"]))
    return dict(series)


def compact_and_purge(conn: sqlite3.Connection, cutoff: int, summary_cutoff: int) -> int:
    """Kerää poistettavat lukemat tuntikoosteeseen ja poistaa ne. Palauttaa poistettujen määrän."""
    conn.execute(
        """
        INSERT INTO hourly_summary (source_id, metric, hour_ts, min_value, max_value, sum_value, count)
        SELECT source_id, metric, (ts / 3600) * 3600, MIN(value), MAX(value), SUM(value), COUNT(*)
        FROM readings WHERE ts < ?
        GROUP BY source_id, metric, (ts / 3600) * 3600
        ON CONFLICT (source_id, metric, hour_ts) DO UPDATE SET
            min_value = MIN(hourly_summary.min_value, excluded.min_value),
            max_value = MAX(hourly_summary.max_value, excluded.max_value),
            sum_value = hourly_summary.sum_value + excluded.sum_value,
            count     = hourly_summary.count + excluded.count
        """,
        (cutoff,),
    )
    deleted = conn.execute("DELETE FROM readings WHERE ts < ?", (cutoff,)).rowcount
    conn.execute("DELETE FROM hourly_summary WHERE hour_ts < ?", (summary_cutoff,))
    return deleted


def recent_readings(conn: sqlite3.Connection, source_id: str, metric: str, since: int) -> list[dict[str, Any]]:
    rows = conn.execute(
        "SELECT ts, value FROM readings WHERE source_id = ? AND metric = ? AND ts >= ? ORDER BY ts",
        (source_id, metric, since),
    )
    return [{"t": iso(r["ts"]), "v": r["value"]} for r in rows]


def hourly_history(conn: sqlite3.Connection, source_id: str, metric: str, since: int) -> list[dict[str, Any]]:
    rows = conn.execute(
        """
        SELECT hour_ts, min_value, max_value, sum_value, count FROM hourly_summary
        WHERE source_id = ? AND metric = ? AND hour_ts >= ? ORDER BY hour_ts
        """,
        (source_id, metric, since),
    )
    return [
        {
            "hour": iso(r["hour_ts"]),
            "min": r["min_value"],
            "max": r["max_value"],
            "avg": round(r["sum_value"] / r["count"], 4),
            "count": r["count"],
        }
        for r in rows
    ]


# ---------------------------------------------------------------- hälytykset

def get_alert(conn: sqlite3.Connection, alert_id: int) -> sqlite3.Row | None:
    return conn.execute("SELECT * FROM alerts WHERE id = ?", (alert_id,)).fetchone()


def active_alerts_for_source(conn: sqlite3.Connection, source_id: str) -> list[sqlite3.Row]:
    return conn.execute(
        "SELECT * FROM alerts WHERE source_id = ? AND status = 'active'", (source_id,)
    ).fetchall()


def insert_alert(conn: sqlite3.Connection, finding: Finding, area: str | None, now: int) -> int:
    cur = conn.execute(
        """
        INSERT INTO alerts (fingerprint, rule_id, source_id, area, severity, category, status, message,
                            value, details, first_seen, last_seen, last_notified, updated_at)
        VALUES (?, ?, ?, ?, ?, ?, 'active', ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            finding.fingerprint, finding.rule.id, finding.source_id, area, finding.severity,
            finding.rule.category, finding.message, finding.value, json.dumps(finding.details),
            now, now, now, now,
        ),
    )
    return int(cur.lastrowid)


def update_alert(conn: sqlite3.Connection, alert_id: int, finding: Finding, now: int) -> None:
    """Uutta tietoa: päivitä sisältö, nosta revisiota ja pyydä uusi analyysi."""
    conn.execute(
        """
        UPDATE alerts SET rule_id = ?, severity = ?, category = ?, message = ?, value = ?, details = ?,
            revision = revision + 1, last_seen = ?, last_notified = ?, updated_at = ?,
            analysis_status = 'pending', analysis_attempts = 0, analysis_retry_at = 0
        WHERE id = ?
        """,
        (
            finding.rule.id, finding.severity, finding.rule.category, finding.message, finding.value,
            json.dumps(finding.details), now, now, now, alert_id,
        ),
    )


def touch_alert(conn: sqlite3.Connection, alert_id: int, now: int) -> None:
    """Tilanne jatkuu ennallaan: päivitetään vain last_seen, ei ilmoitusta."""
    conn.execute("UPDATE alerts SET last_seen = ? WHERE id = ?", (now, alert_id))


def mark_reminded(conn: sqlite3.Connection, alert_id: int, now: int) -> None:
    conn.execute(
        "UPDATE alerts SET last_seen = ?, last_notified = ?, updated_at = ? WHERE id = ?",
        (now, now, now, alert_id),
    )


def resolve_alert(conn: sqlite3.Connection, alert_id: int, now: int, reason: str) -> None:
    row = get_alert(conn, alert_id)
    details = json.loads(row["details"] or "{}")
    details["resolution_reason"] = reason
    conn.execute(
        """
        UPDATE alerts SET status = 'resolved', resolved_at = ?, updated_at = ?, details = ?,
            analysis_status = CASE WHEN analysis_status = 'pending' THEN 'skipped' ELSE analysis_status END
        WHERE id = ?
        """,
        (now, now, json.dumps(details), alert_id),
    )


def add_event(conn: sqlite3.Connection, alert_id: int, event_type: str, now: int) -> dict[str, Any]:
    alert = alert_to_dict(get_alert(conn, alert_id))
    cur = conn.execute(
        "INSERT INTO alert_events (alert_id, event_type, created_at, payload) VALUES (?, ?, ?, ?)",
        (alert_id, event_type, now, json.dumps(alert, ensure_ascii=False)),
    )
    return {"event_id": cur.lastrowid, "event_type": event_type, "created_at": iso(now), "alert": alert}


def list_alerts(conn: sqlite3.Connection, status: str, updated_after: int | None, limit: int) -> list[dict[str, Any]]:
    sql = "SELECT * FROM alerts WHERE 1 = 1"
    params: list[Any] = []
    if status != "all":
        sql += " AND status = ?"
        params.append(status)
    if updated_after is not None:
        sql += " AND updated_at > ?"
        params.append(updated_after)
    sql += f" ORDER BY {SEVERITY_SQL} DESC, updated_at DESC LIMIT ?"
    params.append(limit)
    return [alert_to_dict(r) for r in conn.execute(sql, params)]


def list_events(conn: sqlite3.Connection, after_id: int, limit: int) -> list[dict[str, Any]]:
    rows = conn.execute(
        "SELECT * FROM alert_events WHERE id > ? ORDER BY id LIMIT ?", (after_id, limit)
    )
    return [
        {
            "event_id": r["id"],
            "event_type": r["event_type"],
            "created_at": iso(r["created_at"]),
            "alert": json.loads(r["payload"]),
        }
        for r in rows
    ]


# ---------------------------------------------------------------- agentin analyysi

def pending_analyses(conn: sqlite3.Connection, now: int, limit: int) -> list[sqlite3.Row]:
    return conn.execute(
        f"""
        SELECT * FROM alerts
        WHERE analysis_status = 'pending' AND status = 'active' AND analysis_retry_at <= ?
        ORDER BY {SEVERITY_SQL} DESC, updated_at
        LIMIT ?
        """,
        (now, limit),
    ).fetchall()


def register_analysis_failure(conn: sqlite3.Connection, alert_id: int, now: int) -> int:
    conn.execute(
        """
        UPDATE alerts SET analysis_attempts = analysis_attempts + 1,
            analysis_retry_at = ? + 60 * (analysis_attempts + 1)
        WHERE id = ?
        """,
        (now, alert_id),
    )
    return conn.execute("SELECT analysis_attempts FROM alerts WHERE id = ?", (alert_id,)).fetchone()[0]


def save_analysis(
    conn: sqlite3.Connection, alert_id: int, revision: int, status: str, analysis: dict[str, Any], now: int
) -> bool:
    """Tallentaa vain, jos hälytys ei ole muuttunut analyysin aikana (revision sama)."""
    cur = conn.execute(
        """
        UPDATE alerts SET analysis_status = ?, analysis = ?, updated_at = ?
        WHERE id = ? AND revision = ? AND status = 'active'
        """,
        (status, json.dumps(analysis, ensure_ascii=False), now, alert_id, revision),
    )
    return cur.rowcount == 1


# ---------------------------------------------------------------- ratkaisijat ja pelikirjat

def _resolver_dict(row: sqlite3.Row, *, with_contact: bool) -> dict[str, Any]:
    data = {
        "id": row["id"],
        "name": row["name"],
        "category": row["category"],
        "areas": json.loads(row["areas"]),
        "on_call": bool(row["on_call"]),
        "priority": row["priority"],
        "notes": row["notes"],
    }
    if with_contact:
        data["phone"] = row["phone"]
        data["email"] = row["email"]
    return data


def find_resolvers(
    conn: sqlite3.Connection, category: str, area: str | None, limit: int = 5, *, with_contact: bool = True
) -> list[dict[str, Any]]:
    rows = conn.execute(
        "SELECT * FROM resolvers WHERE active = 1 AND category = ?", (category.lower(),)
    ).fetchall()
    wanted = area.casefold() if area else None
    ranked = []
    for row in rows:
        areas = [a.casefold() for a in json.loads(row["areas"])]
        exact = wanted is not None and wanted in areas
        if wanted is None or exact or "*" in areas:
            # Järjestys: oma alue ensin, sitten päivystäjät, sitten sopimusprioriteetti.
            ranked.append(((0 if exact else 1, -row["on_call"], row["priority"], row["name"]), row))
    ranked.sort(key=lambda item: item[0])
    return [_resolver_dict(row, with_contact=with_contact) for _, row in ranked[:limit]]


def resolvers_by_ids(conn: sqlite3.Connection, ids: list[int]) -> dict[int, dict[str, Any]]:
    if not ids:
        return {}
    marks = ",".join("?" * len(ids))
    rows = conn.execute(f"SELECT * FROM resolvers WHERE active = 1 AND id IN ({marks})", ids)
    return {r["id"]: _resolver_dict(r, with_contact=True) for r in rows}


def get_playbook(conn: sqlite3.Connection, rule_id: str) -> dict[str, Any] | None:
    row = conn.execute("SELECT * FROM playbooks WHERE rule_id = ?", (rule_id,)).fetchone()
    if row is None:
        return None
    return {"rule_id": row["rule_id"], "category": row["category"], "actions": json.loads(row["actions"])}
