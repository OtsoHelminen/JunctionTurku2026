import json
from pathlib import Path

import httpx

from app import repository as repo
from app.consolidator import area_from_address, event_metrics, fetch_all, ingest
from app.db import connect, session
from app.jobs import evaluate_all
from app.models import HouseEvents
from conftest import T0

EXAMPLE = json.loads((Path(__file__).resolve().parent.parent / "examples" / "input.json").read_text())


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
    }


def test_ingest_stores_readings_and_estate(settings):
    with session(settings.db_path) as conn:
        assert ingest(conn, HouseEvents.model_validate(EXAMPLE), T0) == 7
        assert ingest(conn, HouseEvents.model_validate({**EXAMPLE, "data_events": []}), T0 + 60) == 0
    conn = connect(settings.db_path)
    source = conn.execute("SELECT * FROM sources").fetchone()
    estate = repo.get_estate(conn, "house-1")
    conn.close()
    assert source["source_id"] == "house-1" and source["area"] == "Helsinki"
    assert source["last_seen"] == T0  # tyhjä vastaus ei päivitä -> no_data huomaa katkon
    assert estate["construction_year"] == 1978 and estate["renovation_years"] == [1998, 2015]


def test_fetch_all_skips_broken_house_and_alerts_flow(settings, rules):
    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/app/houses":
            return httpx.Response(200, json={"houses": [{"id": 1}, {"id": 2}]})
        if request.url.path == "/app/data_events/1":
            return httpx.Response(200, json=EXAMPLE)
        return httpx.Response(503, json={"detail": "Event history incomplete"})

    payloads = fetch_all("http://consolidator", 5, transport=httpx.MockTransport(handler))
    assert [p.house.id for p in payloads] == [1]

    with session(settings.db_path) as conn:
        for minute in range(15):
            ingest(conn, payloads[0], T0 + minute * 60)
    events = evaluate_all(settings, rules, T0 + 15 * 60, full=True)
    created = {(e["alert"]["rule_id"], e["alert"]["source_id"]) for e in events if e["event_type"] == "created"}
    # esimerkkidatassa rankkasade, myrsky tänään ja pakkasta ennusteessa
    assert created == {("heavy_rain", "house-1"), ("storm_wind", "house-1"), ("frost_forecast", "house-1")}
