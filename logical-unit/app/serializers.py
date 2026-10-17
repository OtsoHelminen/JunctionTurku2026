"""Hälytysten JSON-muoto, jota App lukee."""

from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timezone
from typing import Any


def iso(ts: int | None) -> str | None:
    if ts is None:
        return None
    return datetime.fromtimestamp(ts, tz=timezone.utc).isoformat().replace("+00:00", "Z")


def alert_to_dict(row: sqlite3.Row) -> dict[str, Any]:
    analysis: dict[str, Any] = {"status": row["analysis_status"]}
    if row["analysis"]:
        analysis.update(json.loads(row["analysis"]))
    return {
        "alert_id": row["id"],
        "fingerprint": row["fingerprint"],
        "rule_id": row["rule_id"],
        "source_id": row["source_id"],
        "area": row["area"],
        "severity": row["severity"],
        "category": row["category"],
        "status": row["status"],
        "message": row["message"],
        "value": row["value"],
        "details": json.loads(row["details"] or "{}"),
        "revision": row["revision"],
        "first_seen": iso(row["first_seen"]),
        "last_seen": iso(row["last_seen"]),
        "last_notified": iso(row["last_notified"]),
        "resolved_at": iso(row["resolved_at"]),
        "updated_at": iso(row["updated_at"]),
        "analysis": analysis,
    }
