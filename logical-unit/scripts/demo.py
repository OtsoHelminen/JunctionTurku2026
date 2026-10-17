"""Nopea simulaatio: neljä tuntia dataa muutamassa sekunnissa, ilman palvelinta ja ilman kielimallia.

Ajo projektin juuresta:  python scripts/demo.py
Data on Data Consolidatorin muotoista (examples/input.json) ja kulkee saman adapterin
(app/consolidator.py) läpi kuin oikea haku. Näyttää, mitä hälytystapahtumia syntyy ja
miltä App:lle menevä hälytys-JSON näyttää.
"""

from __future__ import annotations

import copy
import json
import random
import sys
import tempfile
from dataclasses import replace
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app import repository as repo  # noqa: E402
from app.agent.worker import process_pending  # noqa: E402
from app.config import PROJECT_ROOT, load_settings  # noqa: E402
from app.consolidator import ingest  # noqa: E402
from app.db import connect, init_db, session  # noqa: E402
from app.jobs import hourly_evaluation, minute_tick  # noqa: E402
from app.models import HouseEvents  # noqa: E402
from app.rules import load_rules  # noqa: E402
from app.seed import apply_seed, load_seed_file  # noqa: E402
from app.serializers import iso  # noqa: E402

T0 = 1_792_220_400  # 2026-10-17 07:00 UTC
SOURCE = "house-1"
TEMPLATE = json.loads((PROJECT_ROOT / "examples" / "input.json").read_text(encoding="utf-8"))
rng = random.Random(42)


def scenario(minute: int) -> HouseEvents:
    """Consolidatorin vastaus kohteelle 1: normaali -> myrsky lähestyy -> kova myrsky -> tyyntyy."""
    rain, wind, extremes = 1.0, 5.0, []            # normaali syyssää
    if 90 <= minute < 185:                         # myrsky lähestyy: sade ja tuuli voimistuvat
        rain = min(14.0, 1.0 + (minute - 90) * 0.3)
        wind = min(18.0, 5.0 + (minute - 90) * 0.3)
    if 150 <= minute < 185:                        # consolidator: tulvavaroitus vyöhykkeelle
        extremes = [{"type": "flood", "severity": "warning"}]
    if 185 <= minute < 190:                        # kova myrsky
        rain, wind = 28.0, 24.0
        extremes = [{"type": "flood", "severity": "severe"}]
    payload = copy.deepcopy(TEMPLATE)
    event = payload["data_events"][0]
    event["timestamp"] = iso(T0 + minute * 60)
    event["extremes"] = extremes
    for i, day in enumerate(event["weather"]["forecast"]):
        day["rainfall_mm"] = round(rain / (i + 1) + rng.uniform(0, 0.3), 1)
        day["wind"]["speed_m_s"] = round(wind / (i + 1) + rng.uniform(0, 0.3), 1)
        day["temperature"] = {"min_c": round(6 + i + rng.uniform(-0.3, 0.3), 1), "max_c": 12.0 + i}
    return HouseEvents.model_validate(payload)


def main() -> None:
    tmp = Path(tempfile.mkdtemp())
    settings = replace(load_settings(), db_path=str(tmp / "demo.db"), agent_enabled=False)
    init_db(settings.db_path)
    with session(settings.db_path) as conn:
        apply_seed(conn, load_seed_file(PROJECT_ROOT / "config" / "resolvers.yaml"))
    rules = load_rules(settings.rules_path)

    print("Simuloidaan 4 h: normaali -> myrsky lähestyy (90 min) -> kova myrsky (185 min) -> tyyntyy (190 min)\n")
    timeline = []
    for minute in range(0, 241):
        now = T0 + minute * 60
        with session(settings.db_path) as conn:          # sama kuin consolidatorin haku
            ingest(conn, scenario(minute), now, settings)
        timeline += minute_tick(settings, rules, now)     # joka minuutti
        if minute > 0 and minute % 60 == 0:               # tasatunnein
            timeline += hourly_evaluation(settings, rules, now)
        process_pending(settings, None, now=now, limit=10)  # analyysi (tässä pelikirja, ei mallia)

    print(f"{'aika (UTC)':<22}{'tapahtuma':<11}{'vakavuus':<10}viesti")
    for event in timeline:
        a = event["alert"]
        print(f"{event['created_at']:<22}{event['event_type']:<11}{a['severity']:<10}{a['message']}")

    conn = connect(settings.db_path)
    analyzed = conn.execute(
        "SELECT payload FROM alert_events WHERE event_type = 'analyzed' ORDER BY id LIMIT 1"
    ).fetchone()
    summaries = repo.hourly_history(conn, SOURCE, "wind_today_m_s", 0)
    conn.close()

    print("\nEsimerkki App:lle menevästä hälytys-JSONista (analyysin jälkeen):")
    print(json.dumps(json.loads(analyzed["payload"]), ensure_ascii=False, indent=2))
    print("\nTuntikoosteet (tuuli m/s) säilyvät, vaikka raakadata poistetaan:")
    for row in summaries:
        print(f"  {row['hour']}  min {row['min']:.2f}  max {row['max']:.2f}  avg {row['avg']:.2f}  ({row['count']} lukemaa)")
    print(f"\nKanta: {settings.db_path}  (viimeisin hetki {iso(T0 + 240 * 60)})")


if __name__ == "__main__":
    main()
