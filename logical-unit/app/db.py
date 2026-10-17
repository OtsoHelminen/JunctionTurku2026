"""SQLite-yhteydet. WAL-tila sallii lukemisen samaan aikaan kun ajastin kirjoittaa."""

from __future__ import annotations

import sqlite3
from contextlib import contextmanager
from pathlib import Path
from typing import Iterator

_SCHEMA_PATH = Path(__file__).with_name("schema.sql")


def connect(db_path: str) -> sqlite3.Connection:
    # isolation_level=None: transaktiot hallitaan itse (BEGIN IMMEDIATE alla).
    conn = sqlite3.connect(db_path, timeout=30, isolation_level=None)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA synchronous=NORMAL")
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


@contextmanager
def transaction(conn: sqlite3.Connection) -> Iterator[sqlite3.Connection]:
    """Kirjoitustransaktio: commit onnistuessa, rollback virheessä."""
    conn.execute("BEGIN IMMEDIATE")
    try:
        yield conn
    except BaseException:
        conn.execute("ROLLBACK")
        raise
    conn.execute("COMMIT")


@contextmanager
def session(db_path: str) -> Iterator[sqlite3.Connection]:
    """Avaa yhteyden ja ajaa lohkon yhtenä kirjoitustransaktiona."""
    conn = connect(db_path)
    try:
        with transaction(conn):
            yield conn
    finally:
        conn.close()


def init_db(db_path: str) -> None:
    Path(db_path).parent.mkdir(parents=True, exist_ok=True)
    conn = connect(db_path)
    try:
        conn.executescript(_SCHEMA_PATH.read_text(encoding="utf-8"))
        columns = {row["name"] for row in conn.execute("PRAGMA table_info(sources)")}
        if "estate" not in columns:  # vanha kanta ennen Data Consolidator -integraatiota
            conn.execute("ALTER TABLE sources ADD COLUMN estate TEXT")
    finally:
        conn.close()
