"""Asetukset luetaan ympäristömuuttujista."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent


def _env_bool(name: str, default: bool) -> bool:
    raw = os.getenv(name)
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on"}


@dataclass(frozen=True)
class Settings:
    db_path: str
    rules_path: str
    seed_path: str
    retention_minutes: int           # raakadatan säilytys (liukuva ikkuna)
    summary_retention_days: int      # tuntikoosteiden säilytys
    evaluation_interval_minutes: int # täysi sääntöarviointi (oletus kerran tunnissa)
    tick_seconds: int                # minuuttiajon väli
    renotify_hours: float            # muuttumaton hälytys muistutetaan näin harvoin
    change_threshold_pct: float      # arvon muutos, joka lasketaan "uudeksi tiedoksi"
    max_future_skew_seconds: int     # kuinka paljon tulevaisuuteen aikaleima saa olla
    consolidator_enabled: bool       # hae data Data Consolidatorilta
    consolidator_url: str
    consolidator_timeout_seconds: float
    poll_seconds: int                # datan hakuväli
    notify_enabled: bool             # push-ilmoitukset Appiin consolidatorin kautta
    notify_events: frozenset[str]    # tapahtumat, joista ilmoitetaan
    notify_seconds: int              # ilmoitusjonon tarkistusväli
    notify_max_attempts: int
    scheduler_enabled: bool
    admin_endpoints: bool
    agent_enabled: bool
    llm_base_url: str
    llm_model: str
    llm_api_key: str
    llm_timeout_seconds: float
    agent_max_steps: int
    agent_max_attempts: int


def load_settings() -> Settings:
    return Settings(
        db_path=os.getenv("DB_PATH", str(PROJECT_ROOT / "data" / "alerts.db")),
        rules_path=os.getenv("RULES_PATH", str(PROJECT_ROOT / "config" / "rules.yaml")),
        seed_path=os.getenv("SEED_PATH", str(PROJECT_ROOT / "config" / "resolvers.yaml")),
        retention_minutes=int(os.getenv("RETENTION_MINUTES", "60")),
        summary_retention_days=int(os.getenv("SUMMARY_RETENTION_DAYS", "30")),
        evaluation_interval_minutes=int(os.getenv("EVALUATION_INTERVAL_MINUTES", "60")),
        tick_seconds=int(os.getenv("TICK_SECONDS", "60")),
        renotify_hours=float(os.getenv("RENOTIFY_HOURS", "6")),
        change_threshold_pct=float(os.getenv("CHANGE_THRESHOLD_PCT", "10")),
        max_future_skew_seconds=int(os.getenv("MAX_FUTURE_SKEW_SECONDS", "300")),
        consolidator_enabled=_env_bool("CONSOLIDATOR_ENABLED", True),
        consolidator_url=os.getenv("CONSOLIDATOR_URL", "http://localhost:8008"),
        consolidator_timeout_seconds=float(os.getenv("CONSOLIDATOR_TIMEOUT_SECONDS", "10")),
        poll_seconds=int(os.getenv("POLL_SECONDS", "60")),
        notify_enabled=_env_bool("NOTIFY_ENABLED", True),
        notify_events=frozenset(
            e.strip() for e in os.getenv("NOTIFY_EVENTS", "created,escalated,resolved,analyzed").split(",") if e.strip()
        ),
        notify_seconds=int(os.getenv("NOTIFY_SECONDS", "5")),
        notify_max_attempts=int(os.getenv("NOTIFY_MAX_ATTEMPTS", "5")),
        scheduler_enabled=_env_bool("SCHEDULER_ENABLED", True),
        admin_endpoints=_env_bool("ENABLE_ADMIN_ENDPOINTS", False),
        agent_enabled=_env_bool("AGENT_ENABLED", False),
        llm_base_url=os.getenv("LLM_BASE_URL", "http://localhost:11434/v1"),
        llm_model=os.getenv("LLM_MODEL", "qwen3:8b"),
        llm_api_key=os.getenv("LLM_API_KEY", "ollama"),
        llm_timeout_seconds=float(os.getenv("LLM_TIMEOUT_SECONDS", "120")),
        agent_max_steps=int(os.getenv("AGENT_MAX_STEPS", "6")),
        agent_max_attempts=int(os.getenv("AGENT_MAX_ATTEMPTS", "3")),
    )
