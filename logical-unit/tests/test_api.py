import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

EXAMPLE = Path(__file__).resolve().parent.parent / "examples" / "input.json"


@pytest.fixture
def client(settings, monkeypatch):
    monkeypatch.setenv("DB_PATH", settings.db_path)
    monkeypatch.setenv("SCHEDULER_ENABLED", "false")
    monkeypatch.setenv("ENABLE_ADMIN_ENDPOINTS", "true")
    from app.main import create_app

    with TestClient(create_app()) as c:
        yield c


def house_events(house_id=1, address="Koivukuja 12, 00930 Helsinki, Finland", **day):
    event = json.loads(EXAMPLE.read_text())["data_events"][0]
    del event["timestamp"]  # ilman aikaleimaa = vastaanottohetki
    event["weather"]["forecast"][0].update(day)
    return {"house": {"id": house_id, "address": address}, "data_events": [event]}


def test_health(client):
    body = client.get("/health").json()
    assert body["status"] == "ok" and body["rules"] == 13


def test_input_single_and_batch(client):
    r = client.post("/input", json=house_events())
    assert r.status_code == 202 and r.json()["accepted_readings"] == 9

    batch = [house_events(1), {"house": {"id": 2, "address": "Testitie 1, 02100 Espoo, Finland"}, "data_events": []}]
    r = client.post("/input", json=batch)
    assert r.json() == {"accepted_readings": 9, "houses_without_events": 1}


def test_input_validation(client):
    future = house_events()
    future["data_events"][0]["timestamp"] = "2099-01-01T00:00:00Z"
    assert client.post("/input", json=future).json()["accepted_readings"] == 0
    assert client.post("/input", json={"data_events": []}).status_code == 422
    assert client.post("/input", json=house_events(rainfall_mm=-1)).status_code == 422
    assert client.post("/input", json=house_events(wind={"speed_m_s": "kova"})).status_code == 422


def test_critical_input_flows_to_alerts_and_events(client):
    client.post("/input", json=house_events(9, "Testitie 1, 02100 Espoo, Finland", wind={"speed_m_s": 24.0}))
    events = client.post("/admin/evaluate").json()["events"]
    assert any(e["alert"]["rule_id"] == "severe_storm" for e in events)

    alerts = client.get("/alerts").json()["alerts"]
    storm = next(a for a in alerts if a["rule_id"] == "severe_storm")
    assert storm["severity"] == "critical" and storm["area"] == "Espoo" and storm["source_id"] == "house-9"
    assert client.get(f"/alerts/{storm['alert_id']}").status_code == 200
    assert client.get("/alerts/99999").status_code == 404

    feed = client.get("/events", params={"after_id": 0}).json()
    assert feed["events"] and feed["last_id"] == feed["events"][-1]["event_id"]
    assert client.get("/events", params={"after_id": feed["last_id"]}).json()["events"] == []
