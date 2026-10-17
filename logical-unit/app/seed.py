"""Ratkaisijoiden ja pelikirjojen lataus YAML-tiedostosta tietokantaan.

Käyttö:  python -m app.seed [polku/resolvers.yaml]
"""

from __future__ import annotations

import json
import logging
import sqlite3
import sys
from pathlib import Path
from typing import Any

import yaml

from .config import Settings, load_settings
from .db import connect, init_db, session

log = logging.getLogger(__name__)


def apply_seed(conn: sqlite3.Connection, data: dict[str, Any]) -> tuple[int, int]:
    resolvers = data.get("resolvers") or []
    for r in resolvers:
        areas = r.get("areas") or ["*"]
        conn.execute(
            """
            INSERT INTO resolvers (name, category, areas, phone, email, on_call, priority, notes, active)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT (name) DO UPDATE SET
                category = excluded.category, areas = excluded.areas, phone = excluded.phone,
                email = excluded.email, on_call = excluded.on_call, priority = excluded.priority,
                notes = excluded.notes, active = excluded.active
            """,
            (
                r["name"], str(r["category"]).lower(), json.dumps(areas, ensure_ascii=False),
                r.get("phone"), r.get("email"), int(bool(r.get("on_call", False))),
                int(r.get("priority", 100)), r.get("notes"), int(bool(r.get("active", True))),
            ),
        )
    playbooks = data.get("playbooks") or {}
    for rule_id, pb in playbooks.items():
        conn.execute(
            """
            INSERT INTO playbooks (rule_id, category, actions, expert) VALUES (?, ?, ?, ?)
            ON CONFLICT (rule_id) DO UPDATE SET
                category = excluded.category, actions = excluded.actions, expert = excluded.expert
            """,
            (
                rule_id, str(pb["category"]).lower(), json.dumps(pb.get("actions", []), ensure_ascii=False),
                json.dumps(pb["expert"], ensure_ascii=False) if pb.get("expert") else None,
            ),
        )
    return len(resolvers), len(playbooks)


def load_seed_file(path: str | Path) -> dict[str, Any]:
    return yaml.safe_load(Path(path).read_text(encoding="utf-8")) or {}


def seed_if_empty(settings: Settings) -> None:
    """Käynnistyksessä: täytä vain jos ratkaisijataulu on tyhjä (ei ylikirjoita ylläpidettyä dataa)."""
    path = Path(settings.seed_path)
    if not path.exists():
        return
    conn = connect(settings.db_path)
    try:
        count = conn.execute("SELECT COUNT(*) FROM resolvers").fetchone()[0]
    finally:
        conn.close()
    if count:
        return
    with session(settings.db_path) as conn:
        n_res, n_pb = apply_seed(conn, load_seed_file(path))
    log.info("loaded %d resolvers and %d playbooks from %s", n_res, n_pb, path)


def main() -> None:
    settings = load_settings()
    path = sys.argv[1] if len(sys.argv) > 1 else settings.seed_path
    init_db(settings.db_path)
    with session(settings.db_path) as conn:
        n_res, n_pb = apply_seed(conn, load_seed_file(path))
    print(f"Updated {n_res} resolvers and {n_pb} playbooks ({settings.db_path})")


if __name__ == "__main__":
    main()
