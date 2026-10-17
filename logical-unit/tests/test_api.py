import time

import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def client(settings, monkeypatch):
    monkeypatch.setenv("DB_PATH", settings.db_path)
    monkeypatch.setenv("SCHEDULER_ENABLED", "false")
    monkeypatch.setenv("ENABLE_ADMIN_ENDPOINTS", "true")
    from app.main import create_app

    with TestClient(create_app()) as c:
        yield c


def test_health(client):
    body = client.get("/health").json()
    assert body["status"] == "ok" and body["rules"] == 8


def test_input_single_and_batch(client):
    r = client.post("/input", json={"source_id": "s1", "area": "Helsinki", "metrics": {"water_pressure_bar": 3.1}})
    assert r.status_code == 202 and r.json()["accepted_readings"] == 1

    batch = [
        {"source_id": "s1", "metrics": {"water_pressure_bar": 3.0, "flow_l_min": 0}},
        {"source_id": "s2", "timestamp": "2020-01-01T00:00:00Z", "metrics": {"x": 1}},
    ]
    r = client.post("/input", json=batch)
    assert r.json() == {"accepted_readings": 2, "skipped_readings": 1}


def test_input_validation(client):
    assert client.post("/input", json={"source_id": "s1", "metrics": {}}).status_code == 422
    assert client.post("/input", json={"metrics": {"a": 1}}).status_code == 422
    future = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(time.time() + 3600))
    r = client.post("/input", json={"source_id": "s1", "timestamp": future, "metrics": {"a": 1}})
    assert r.status_code == 422


def test_critical_input_flows_to_alerts_and_events(client):
    client.post("/input", json={"source_id": "s9", "area": "Espoo", "metrics": {"water_pressure_bar": 0.4}})
    events = client.post("/admin/evaluate").json()["events"]
    assert any(e["alert"]["rule_id"] == "pressure_critical" for e in events)

    alerts = client.get("/alerts").json()["alerts"]
    assert alerts[0]["severity"] == "critical" and alerts[0]["area"] == "Espoo"
    assert client.get(f"/alerts/{alerts[0]['alert_id']}").status_code == 200
    assert client.get("/alerts/99999").status_code == 404

    feed = client.get("/events", params={"after_id": 0}).json()
    assert feed["events"] and feed["last_id"] == feed["events"][-1]["event_id"]
    assert client.get("/events", params={"after_id": feed["last_id"]}).json()["events"] == []
