from __future__ import annotations

import sys
from dataclasses import replace
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from app.config import load_settings  # noqa: E402
from app.db import init_db, session  # noqa: E402
from app.rules import load_rules  # noqa: E402
from app.seed import apply_seed, load_seed_file  # noqa: E402

T0 = 1_792_220_400  # 2026-10-17 07:00:00 UTC, tasatunti


@pytest.fixture
def settings(tmp_path):
    s = replace(
        load_settings(),
        db_path=str(tmp_path / "test.db"),
        rules_path=str(ROOT / "config" / "rules.yaml"),
        seed_path=str(ROOT / "config" / "resolvers.yaml"),
        agent_enabled=False,
    )
    init_db(s.db_path)
    with session(s.db_path) as conn:
        apply_seed(conn, load_seed_file(s.seed_path))
    return s


@pytest.fixture
def rules(settings):
    return load_rules(settings.rules_path)
