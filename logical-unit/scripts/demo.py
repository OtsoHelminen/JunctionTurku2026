"""Nopea simulaatio: neljä tuntia dataa muutamassa sekunnissa, ilman palvelinta ja ilman kielimallia.

Ajo projektin juuresta:  python scripts/demo.py
Näyttää, mitä hälytystapahtumia syntyy ja miltä App:lle menevä hälytys-JSON näyttää.
"""

from __future__ import annotations

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
from app.db import connect, init_db, session  # noqa: E402
from app.jobs import hourly_evaluation, minute_tick  # noqa: E402
from app.rules import load_rules  # noqa: E402
from app.seed import apply_seed, load_seed_file  # noqa: E402
from app.serializers import iso  # noqa: E402

T0 = 1_792_220_400  # 2026-10-17 07:00 UTC
SOURCE, AREA = "site-42", "Helsinki"
rng = random.Random(42)


def scenario(minute: int) -> dict[str, float]:
    pressure, flow = 3.0, (1.2 if rng.random() < 0.15 else 0.0)  # normaali: satunnaista käyttöä
    if 90 <= minute < 185:                                       # vuoto alkaa
        pressure = max(1.7, 3.0 - (minute - 90) * 0.04)
        flow = 2.5
    if 185 <= minute < 190:                                      # paine romahtaa
        pressure, flow = 0.8, 4.0
    return {
        "water_pressure_bar": round(pressure + rng.uniform(-0.03, 0.03), 3),
        "flow_l_min": flow,
        "temperature_c": round(19 + rng.uniform(-0.3, 0.3), 2),
        "humidity_pct": round(45 + rng.uniform(-2, 2), 1),
    }


def main() -> None:
    tmp = Path(tempfile.mkdtemp())
    settings = replace(load_settings(), db_path=str(tmp / "demo.db"), agent_enabled=False)
    init_db(settings.db_path)
    with session(settings.db_path) as conn:
        apply_seed(conn, load_seed_file(PROJECT_ROOT / "config" / "resolvers.yaml"))
    rules = load_rules(settings.rules_path)

    print("Simuloidaan 4 h: normaali -> vuoto (90 min) -> paineen romahdus (185 min) -> korjaus (190 min)\n")
    timeline = []
    for minute in range(0, 241):
        now = T0 + minute * 60
        with session(settings.db_path) as conn:          # sama kuin POST /input
            repo.upsert_source(conn, SOURCE, AREA, now)
            repo.insert_readings(conn, SOURCE, now, scenario(minute))
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
    summaries = repo.hourly_history(conn, SOURCE, "water_pressure_bar", 0)
    conn.close()

    print("\nEsimerkki App:lle menevästä hälytys-JSONista (analyysin jälkeen):")
    print(json.dumps(json.loads(analyzed["payload"]), ensure_ascii=False, indent=2))
    print("\nTuntikoosteet säilyvät, vaikka raakadata poistetaan:")
    for row in summaries:
        print(f"  {row['hour']}  min {row['min']:.2f}  max {row['max']:.2f}  avg {row['avg']:.2f}  ({row['count']} lukemaa)")
    print(f"\nKanta: {settings.db_path}  (viimeisin hetki {iso(T0 + 240 * 60)})")


if __name__ == "__main__":
    main()
