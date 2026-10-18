import json
from dataclasses import replace

import httpx

from app import repository as repo
from app.agent.worker import process_pending
from app.db import connect, session
from app.jobs import evaluate_all, minute_tick
from app.notifier import Notifier
from conftest import T0
from test_lifecycle import feed, normal, rainy, weather


class FakeConsolidator:
    """MockTransport, joka tallentaa POST /app/notify -kutsut ja voi vastata virheellä."""

    def __init__(self, fail=0):
        self.fail = fail
        self.sent = []

    def __call__(self, request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/app/notify"
        if self.fail:
            self.fail -= 1
            return httpx.Response(502, json={"detail": "Expo push service request failed"})
        self.sent.append(json.loads(request.content))
        return httpx.Response(200, json={"sent": 1, "tickets": [], "removed_tokens": []})


def notifier(settings, fake, **overrides):
    return Notifier(replace(settings, **overrides), transport=httpx.MockTransport(fake))


def cursor(settings):
    conn = connect(settings.db_path)
    try:
        return repo.notifier_cursor(conn)
    finally:
        conn.close()


def test_alert_lifecycle_is_pushed_to_app(settings, rules):
    fake = FakeConsolidator()
    n = notifier(settings, fake)

    feed(settings, 0, 61, rainy)
    evaluate_all(settings, rules, T0 + 60 * 60, full=True)          # created
    process_pending(settings, None, now=T0 + 60 * 60, limit=10)      # analyzed (pelikirja)
    feed(settings, 61, 63, lambda m: weather(rain=30.0))
    minute_tick(settings, rules, T0 + 62 * 60)                        # escalated
    feed(settings, 63, 121, normal)
    evaluate_all(settings, rules, T0 + 120 * 60, full=True)          # resolved

    assert n.run_once() == 4
    assert [p["data"]["event_type"] for p in fake.sent] == ["created", "analyzed", "escalated", "resolved"]

    created, analyzed, escalated, resolved = fake.sent
    assert created["title"] == "High alert – Helsinki"
    assert created["data"]["kind"] == "alert" and created["data"]["house_id"] == 1
    assert created["data"]["rule_id"] == "heavy_rain"
    assert analyzed["body"] == ("Clean the gutters and downspouts before the rain"
                                "\nSuggested expert: Roofer, approx. 150–400 €")
    assert analyzed["data"]["expert"] == {
        "registered": False, "profession": "Roofer", "example_name": "Example Roofing Ltd",
        "price_min_eur": 150, "price_max_eur": 400,
    }
    assert created["data"]["expert"] is None  # analyysi ei vielä valmis
    assert escalated["title"] == "Alert escalated: Critical – Helsinki"
    assert resolved["data"]["status"] == "resolved"
    assert all("sound" not in payload for payload in fake.sent)
    assert len({p["data"]["alert_id"] for p in fake.sent}) == 1

    assert n.run_once() == 0  # kursori eteni, ei tuplailmoituksia
    with session(settings.db_path) as conn:
        assert cursor(settings) == repo.list_events(conn, 0, 100)[-1]["event_id"]


def test_failed_push_is_retried_without_losing_events(settings, rules):
    fake = FakeConsolidator(fail=2)
    n = notifier(settings, fake)
    feed(settings, 0, 5, lambda m: weather(wind=24.0))
    minute_tick(settings, rules, T0 + 4 * 60)

    assert n.run_once() == 0 and n.run_once() == 0
    assert cursor(settings) == 0
    assert n.run_once() == 1
    assert fake.sent[0]["data"]["rule_id"] == "severe_storm"


def test_permanently_failing_push_is_skipped(settings, rules):
    fake = FakeConsolidator(fail=100)
    n = notifier(settings, fake, notify_max_attempts=2)
    feed(settings, 0, 5, lambda m: weather(wind=24.0))
    minute_tick(settings, rules, T0 + 4 * 60)

    n.run_once()
    n.run_once()  # 2. yritys -> ohitetaan
    assert cursor(settings) > 0 and fake.sent == []


def test_event_filter(settings, rules):
    fake = FakeConsolidator()
    n = notifier(settings, fake, notify_events=frozenset({"resolved"}))
    feed(settings, 0, 5, lambda m: weather(wind=24.0))
    minute_tick(settings, rules, T0 + 4 * 60)
    assert n.run_once() == 0 and cursor(settings) > 0  # created ohitettu, kursori silti eteni


def test_startup_cursor_skips_old_history(settings, rules):
    feed(settings, 0, 5, lambda m: weather(wind=24.0))
    minute_tick(settings, rules, T0 + 4 * 60)
    with session(settings.db_path) as conn:
        repo.init_notifier_cursor(conn)
    fake = FakeConsolidator()
    assert notifier(settings, fake).run_once() == 0
