import copy
from dataclasses import replace
import json
from pathlib import Path

import httpx

from app import repository as repo
from app.consolidator import area_from_address, event_metrics, fetch_all, ingest
from app.db import connect, session
from app.jobs import evaluate_all, minute_tick
from app.models import HouseEvents
from app.serializers import iso
from conftest import T0

EXAMPLE = json.loads((Path(__file__).resolve().parent.parent / "examples" / "input.json").read_text())


def house_events(minutes, *, extremes=None):
    """Consolidatorin vastaus, jossa tapahtuma joka annetulle minuutille (uusin ensin)."""
    payload = copy.deepcopy(EXAMPLE)
    template = payload["data_events"][0]
    events = []
    for m in sorted(minutes, reverse=True):
        event = copy.deepcopy(template)
        event["timestamp"] = iso(T0 + m * 60)
        if extremes is not None:
            event["extremes"] = extremes
        events.append(event)
    payload["data_events"] = events
    return HouseEvents.model_validate(payload)


def test_area_from_address():
    assert area_from_address("Koivukuja 12, 00930 Helsinki, Finland") == "Helsinki"
    assert area_from_address("Testitie 1, 02100 Espoo") == "Espoo"
    assert area_from_address("Helsinki") is None


def test_event_metrics():
    metrics = event_metrics(HouseEvents.model_validate(EXAMPLE).data_events[0])
    assert metrics == {
        "rain_today_mm": 12.4,
        "wind_today_m_s": 16.2,
        "temp_min_today_c": 7.9,
        "temp_max_today_c": 13.8,
        "rain_forecast_total_mm": 18.5,
        "wind_forecast_max_m_s": 16.2,
        "temp_forecast_min_c": -0.5,
        "flood_level": 1.0,
        "forest_fire_level": 0.0,
        "frostbite_level": 0.0,
        "freezing_pipes_level": 0.0,
    }


def test_ingest_uses_event_timestamps_and_window(settings):
    settings = replace(settings, max_future_skew_seconds=300)
    now = T0 + 70 * 60
    # minuutit 0..9 ovat yli 60 min vanhoja, 80 on yli 5 min tulevaisuudessa -> ohitetaan
    payload = house_events([*range(0, 70), 80])
    with session(settings.db_path) as conn:
        stored = ingest(conn, payload, now, settings)
        assert ingest(conn, payload, now, settings) == stored  # idempotentti: ei tuplarivejä
    conn = connect(settings.db_path)
    source = conn.execute("SELECT * FROM sources").fetchone()
    timestamps = [r[0] for r in conn.execute("SELECT DISTINCT ts FROM readings ORDER BY ts")]
    estate = repo.get_estate(conn, "house-1")
    conn.close()
    assert stored == 60 * 11
    assert timestamps == [T0 + m * 60 for m in range(10, 70)]
    assert source["source_id"] == "house-1" and source["area"] == "Helsinki"
    assert source["last_seen"] == T0 + 69 * 60
    assert estate["construction_year"] == 1978 and "id" not in estate and "created_at" not in estate


def test_ingest_accepts_consolidator_clock_running_ahead(settings, rules):
    # Jokainen /app/simulate/* siirtää consolidatorin kelloa minuutin edelle.
    now = T0 + 20 * 60
    with session(settings.db_path) as conn:
        assert ingest(conn, house_events(range(10, 31)), now, settings) == 21 * 11
    events = minute_tick(settings, rules, now)
    assert {e["alert"]["rule_id"] for e in events} == {"flood_warning"}


def test_consolidator_frost_extremes_alert_immediately(settings, rules):
    frost = [{"type": "freezing_pipes", "severity": "severe"}, {"type": "frostbite", "severity": "warning"}]
    with session(settings.db_path) as conn:
        ingest(conn, house_events(range(0, 3), extremes=frost), T0 + 2 * 60, settings)
    events = minute_tick(settings, rules, T0 + 2 * 60)
    created = {e["alert"]["rule_id"] for e in events if e["event_type"] == "created"}
    assert {"freezing_pipes_severe", "frostbite_warning"} <= created


def test_simulated_extreme_is_caught_after_weather_returns_to_normal(settings, rules):
    # Consolidatorin simulointi kirjoittaa ääri-ilmiön historiaan kerralla, ja seuraava
    # minuutti on jo normaali. Hälytys syntyy silti, vaikka uusin arvo on normaali.
    storm = [{"type": "flood", "severity": "severe"}]
    with session(settings.db_path) as conn:
        ingest(conn, house_events(range(0, 10), extremes=storm), T0 + 9 * 60, settings)
        ingest(conn, house_events(range(10, 12), extremes=[]), T0 + 11 * 60, settings)
    events = minute_tick(settings, rules, T0 + 11 * 60)
    assert "flood_severe" in {e["alert"]["rule_id"] for e in events if e["event_type"] == "created"}


def test_ingest_without_valid_events_stores_nothing(settings):
    with session(settings.db_path) as conn:
        assert ingest(conn, house_events([]), T0, settings) == 0
        assert ingest(conn, house_events([0]), T0 + 3 * 3600, settings) == 0  # liian vanha
        assert repo.list_sources(conn) == []  # no_data huomaa katkon


def test_consolidator_extremes_alert_escalate_and_clear(settings, rules):
    severe = [{"type": "flood", "severity": "severe"}, {"type": "forest_fire", "severity": "warning"}]
    with session(settings.db_path) as conn:
        ingest(conn, house_events(range(0, 5), extremes=[]), T0 + 4 * 60, settings)
        ingest(conn, house_events(range(5, 8), extremes=severe), T0 + 7 * 60, settings)
    events = minute_tick(settings, rules, T0 + 7 * 60)
    created = {(e["event_type"], e["alert"]["rule_id"]) for e in events}
    assert {("created", "flood_severe"), ("created", "forest_fire_warning")} <= created

    with session(settings.db_path) as conn:  # max 10 min ikkunassa: kuittautuu 10 min jälkeen
        ingest(conn, house_events(range(8, 19), extremes=[]), T0 + 18 * 60, settings)
    events = evaluate_all(settings, rules, T0 + 18 * 60, full=True)
    resolved = {e["alert"]["rule_id"] for e in events if e["event_type"] == "resolved"}
    assert {"flood_severe", "forest_fire_warning"} <= resolved


def test_fetch_all_skips_broken_house_and_alerts_flow(settings, rules):
    payload = house_events(range(0, 16)).model_dump(mode="json")

    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/app/houses":
            return httpx.Response(200, json={"houses": [{"id": 1}, {"id": 2}]})
        if request.url.path == "/app/data_events/1":
            return httpx.Response(200, json=payload)
        return httpx.Response(500, text="Internal Server Error")

    payloads = fetch_all("http://consolidator", 5, transport=httpx.MockTransport(handler))
    assert [p.house.id for p in payloads] == [1]

    now = T0 + 15 * 60
    with session(settings.db_path) as conn:
        ingest(conn, payloads[0], now, settings)
    events = evaluate_all(settings, rules, now, full=True)
    created = {e["alert"]["rule_id"] for e in events if e["event_type"] == "created"}
    # esimerkkidatassa rankkasade, myrsky tänään, pakkasta ennusteessa ja tulvavaroitus
    assert created == {"heavy_rain", "storm_wind", "frost_forecast", "flood_warning"}
