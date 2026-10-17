"""Reaaliaikainen simulaattori: lähettää käynnissä olevalle palvelulle JSONin minuutin välein,
kuten Data Consolidator tekisi. Ei riippuvuuksia (vain standardikirjasto).

  python scripts/send_sample.py                      # normaali data joka minuutti
  python scripts/send_sample.py --scenario leak      # vuoto: paine laskee, virtaus jatkuu
  python scripts/send_sample.py --interval 5         # nopeampi tahti testaukseen
"""

from __future__ import annotations

import argparse
import json
import random
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone


def build(source: str, area: str, scenario: str, step: int) -> dict:
    pressure, flow = 3.0 + random.uniform(-0.03, 0.03), (1.2 if random.random() < 0.15 else 0.0)
    if scenario == "leak":
        pressure = max(0.8, 3.0 - step * 0.05) + random.uniform(-0.02, 0.02)
        flow = 2.5
    elif scenario == "freeze":
        return {
            "source_id": source, "area": area,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "metrics": {"temperature_c": 1.5, "water_pressure_bar": pressure, "flow_l_min": 0.0},
        }
    return {
        "source_id": source,
        "area": area,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "metrics": {
            "water_pressure_bar": round(pressure, 3),
            "flow_l_min": flow,
            "temperature_c": round(19 + random.uniform(-0.3, 0.3), 2),
            "humidity_pct": round(45 + random.uniform(-2, 2), 1),
        },
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--url", default="http://localhost:8000/input")
    parser.add_argument("--source", default="site-42")
    parser.add_argument("--area", default="Helsinki")
    parser.add_argument("--scenario", choices=["normal", "leak", "freeze"], default="normal")
    parser.add_argument("--interval", type=float, default=60)
    args = parser.parse_args()

    step = 0
    while True:
        payload = build(args.source, args.area, args.scenario, step)
        request = urllib.request.Request(
            args.url, data=json.dumps(payload).encode(), headers={"Content-Type": "application/json"}
        )
        try:
            with urllib.request.urlopen(request, timeout=10) as response:
                print(response.status, response.read().decode(), payload["metrics"])
        except urllib.error.URLError as exc:
            print("virhe:", exc)
        step += 1
        time.sleep(args.interval)


if __name__ == "__main__":
    main()
