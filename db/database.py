"""SQLite access layer for houses and alerts.

The database file lives next to this module by default; override the path
with the DATABASE_PATH environment variable or the `path` argument.
"""

from __future__ import annotations

import os
import sqlite3
from pathlib import Path
from typing import Any

DB_DIR = Path(__file__).resolve().parent
SCHEMA_PATH = DB_DIR / "schema.sql"
DEFAULT_DB_PATH = DB_DIR / "consolidator.db"

# Alert thresholds applied to a house's weather forecast.
HEAVY_RAIN_MM = 10.0
STORM_WIND_M_S = 15.0


def connect(path: str | os.PathLike[str] | None = None) -> sqlite3.Connection:
    """Open (creating if needed) the database and ensure the schema exists."""
    db_path = Path(path or os.environ.get("DATABASE_PATH", DEFAULT_DB_PATH))
    # check_same_thread=False: FastAPI runs sync endpoints in a threadpool.
    conn = sqlite3.connect(db_path, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    conn.executescript(SCHEMA_PATH.read_text())
    return conn


def add_house(conn: sqlite3.Connection, estate: dict[str, Any], latitude: float, longitude: float) -> int:
    """Insert a house from an estate payload; returns its id (existing id if the address is known)."""
    cur = conn.execute(
        """
        INSERT INTO houses (address, latitude, longitude, construction_year,
                            house_type, floor_area_m2, number_of_floors, condition)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(address) DO UPDATE SET address = excluded.address
        """,
        (
            estate["address"],
            latitude,
            longitude,
            estate.get("construction_year"),
            estate.get("house_type"),
            estate.get("floor_area_m2"),
            estate.get("number_of_floors"),
            estate.get("condition"),
        ),
    )
    conn.commit()
    if cur.lastrowid:
        return int(cur.lastrowid)
    row = conn.execute("SELECT id FROM houses WHERE address = ?", (estate["address"],)).fetchone()
    return int(row["id"])


def list_houses(conn: sqlite3.Connection) -> list[dict[str, Any]]:
    rows = conn.execute("SELECT * FROM houses ORDER BY id").fetchall()
    return [dict(r) for r in rows]


def get_house(conn: sqlite3.Connection, house_id: int) -> dict[str, Any] | None:
    row = conn.execute("SELECT * FROM houses WHERE id = ?", (house_id,)).fetchone()
    return dict(row) if row else None


def _alerts_for_event(house_id: int, event: dict[str, Any]) -> list[dict[str, Any]]:
    """Derive alerts for one weather event (heavy rain / storm wind per forecast day)."""
    alerts: list[dict[str, Any]] = []
    for day in event["weather"]["forecast"]:
        rain = day["rainfall_mm"]
        wind = day["wind"]["speed_m_s"]
        date = day["date"]
        if rain >= HEAVY_RAIN_MM:
            alerts.append(
                {
                    "house_id": house_id,
                    "alert_type": "heavy_rain",
                    "severity": "high" if rain >= 25 else "medium",
                    "message": f"Heavy rain expected: {rain} mm on {date}",
                    "forecast_date": date,
                }
            )
        if wind >= STORM_WIND_M_S:
            alerts.append(
                {
                    "house_id": house_id,
                    "alert_type": "storm_wind",
                    "severity": "high" if wind >= 20 else "medium",
                    "message": f"Storm wind expected: {wind} m/s on {date}",
                    "forecast_date": date,
                }
            )
    return alerts


def record_alerts(conn: sqlite3.Connection, house_id: int, events: list[dict[str, Any]]) -> int:
    """Store alerts derived from the given events for a house. Returns count inserted."""
    rows = [a for ev in events for a in _alerts_for_event(house_id, ev)]
    conn.executemany(
        "INSERT INTO alerts (house_id, alert_type, severity, message, forecast_date) VALUES (?, ?, ?, ?, ?)",
        [(a["house_id"], a["alert_type"], a["severity"], a["message"], a["forecast_date"]) for a in rows],
    )
    conn.commit()
    return len(rows)


def list_alerts(conn: sqlite3.Connection, house_id: int | None = None) -> list[dict[str, Any]]:
    if house_id is None:
        rows = conn.execute("SELECT * FROM alerts ORDER BY id DESC").fetchall()
    else:
        rows = conn.execute("SELECT * FROM alerts WHERE house_id = ? ORDER BY id DESC", (house_id,)).fetchall()
    return [dict(r) for r in rows]
