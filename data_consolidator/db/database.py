"""SQLite access layer for houses.

The database file lives next to this module by default; override the path
with the DATABASE_PATH environment variable or the `path` argument.
"""

from __future__ import annotations

import math
import os
import sqlite3
from pathlib import Path
from typing import Any

DB_DIR = Path(__file__).resolve().parent
SCHEMA_PATH = DB_DIR / "schema.sql"
DEFAULT_DB_PATH = DB_DIR / "consolidator.db"


def connect(path: str | os.PathLike[str] | None = None) -> sqlite3.Connection:
    """Open (creating if needed) the database and ensure the schema exists."""
    db_path = Path(path or os.environ.get("DATABASE_PATH", DEFAULT_DB_PATH))
    # check_same_thread=False: FastAPI runs sync endpoints in a threadpool.
    conn = sqlite3.connect(db_path, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    conn.executescript(SCHEMA_PATH.read_text())
    return conn


def add_house(
    conn: sqlite3.Connection,
    estate: dict[str, Any],
    latitude: float,
    longitude: float,
    user_id: str,
) -> int:
    """Insert a house from an estate payload; returns its id (existing id if the address is known)."""
    cur = conn.execute(
        """
        INSERT INTO houses (user_id, address, latitude, longitude, construction_year,
                            house_type, floor_area_m2, number_of_floors, condition)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(address) DO UPDATE SET address = excluded.address
        """,
        (
            user_id,
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
    row = conn.execute("SELECT id FROM houses WHERE address = ?",
                       (estate["address"],)).fetchone()
    return int(row["id"])


def list_houses(conn: sqlite3.Connection) -> list[dict[str, Any]]:
    rows = conn.execute("SELECT * FROM houses ORDER BY id").fetchall()
    return [dict(r) for r in rows]


def get_house(conn: sqlite3.Connection, house_id: int) -> dict[str, Any] | None:
    row = conn.execute("SELECT * FROM houses WHERE id = ?",
                       (house_id,)).fetchone()
    return dict(row) if row else None


def haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Great-circle distance between two coordinates in kilometers."""
    r = 6371.0
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp = math.radians(lat2 - lat1)
    dl = math.radians(lon2 - lon1)
    a = math.sin(dp / 2) ** 2 + math.cos(p1) * \
        math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * r * math.asin(math.sqrt(a))


def events_within_radius(
    events: list[dict[str, Any]], latitude: float, longitude: float, radius_km: float
) -> list[dict[str, Any]]:
    """Keep only events whose location is within `radius_km` of the given point."""
    return [
        ev
        for ev in events
        if haversine_km(latitude, longitude, ev["location"]["latitude"], ev["location"]["longitude"])
        <= radius_km
    ]
