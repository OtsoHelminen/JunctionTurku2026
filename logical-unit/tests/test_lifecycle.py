from dataclasses import replace

from app import repository as repo
from app.db import connect, session
from app.jobs import evaluate_all, minute_tick, purge
from conftest import T0


def feed(settings, minute_from, minute_to, metrics_fn, source="house-1", area="Helsinki"):
    with session(settings.db_path) as conn:
        for m in range(minute_from, minute_to):
            ts = T0 + m * 60
            repo.upsert_source(conn, source, area, ts)
            repo.insert_readings(conn, source, ts, metrics_fn(m))


def weather(rain=2.0, wind=5.0, temp_min=5.0):
    """Säämittarit kuten app/consolidator.py ne tallentaa."""
    return {
        "rain_today_mm": rain, "wind_today_m_s": wind,
        "temp_min_today_c": temp_min, "temp_max_today_c": temp_min + 6,
        "rain_forecast_total_mm": rain + 4, "wind_forecast_max_m_s": wind + 1,
        "temp_forecast_min_c": temp_min - 1,
    }


def normal(m):
    return weather(rain=2.0 + (m % 3) * 0.1)


def rainy(m):
    return weather(rain=12.0 + (m % 3) * 0.1)


def types(events):
    return [(e["event_type"], e["alert"]["rule_id"]) for e in events]


def test_full_lifecycle(settings, rules):
    feed(settings, 0, 61, normal)
    assert evaluate_all(settings, rules, T0 + 60 * 60, full=True) == []

    # Ennusteeseen tulee rankkasade tunnin puolivälissä -> heavy_rain
    feed(settings, 61, 91, normal)
    feed(settings, 91, 121, rainy)
    events = evaluate_all(settings, rules, T0 + 120 * 60, full=True)
    assert types(events) == [("created", "heavy_rain")]

    # Sama tilanne jatkuu -> ei uusia hälytyksiä
    feed(settings, 121, 181, rainy)
    assert evaluate_all(settings, rules, T0 + 180 * 60, full=True) == []

    # Erittäin rankka sade -> minuuttiajo eskaloi heti samaa hälytystä
    feed(settings, 181, 183, lambda m: weather(rain=30.0))
    events = minute_tick(settings, rules, T0 + 182 * 60)
    assert types(events) == [("escalated", "extreme_rain")]

    with session(settings.db_path) as conn:
        alerts = repo.list_alerts(conn, "active", None, 50)
    rain = [a for a in alerts if a["fingerprint"] == "rain:house-1"]
    assert len(rain) == 1 and rain[0]["severity"] == "critical" and rain[0]["revision"] == 2

    # Sade väistyy ennusteesta -> kuittaus tuntiajossa
    feed(settings, 183, 241, normal)
    events = evaluate_all(settings, rules, T0 + 240 * 60, full=True)
    assert ("resolved", "extreme_rain") in types(events)


def test_partial_evaluation_never_resolves(settings, rules):
    feed(settings, 0, 5, lambda m: weather(wind=24.0))
    assert types(minute_tick(settings, rules, T0 + 4 * 60)) == [("created", "severe_storm")]
    feed(settings, 5, 10, lambda m: weather(wind=5.0))
    assert minute_tick(settings, rules, T0 + 9 * 60) == []
    with session(settings.db_path) as conn:
        assert len(repo.list_alerts(conn, "active", None, 10)) == 1


def test_missing_data_does_not_resolve_other_alerts(settings, rules):
    feed(settings, 0, 61, rainy)
    evaluate_all(settings, rules, T0 + 60 * 60, full=True)
    # Data loppuu kokonaan: sadehälytys jää, no_data syntyy
    later = T0 + 180 * 60
    purge(settings, later)
    events = evaluate_all(settings, rules, later, full=True)
    assert types(events) == [("created", "no_data")]
    with session(settings.db_path) as conn:
        active = {a["rule_id"] for a in repo.list_alerts(conn, "active", None, 10)}
    assert {"heavy_rain", "no_data"} <= active


def test_reminder_after_quiet_period(settings, rules):
    s = replace(settings, renotify_hours=2)
    feed(s, 0, 61, rainy)
    evaluate_all(s, rules, T0 + 60 * 60, full=True)
    feed(s, 61, 121, rainy)
    assert not any(t == "reminder" for t, _ in types(evaluate_all(s, rules, T0 + 120 * 60, full=True)))
    feed(s, 121, 181, rainy)
    assert ("reminder", "heavy_rain") in types(evaluate_all(s, rules, T0 + 180 * 60, full=True))


def test_purge_keeps_hourly_summary(settings):
    feed(settings, 0, 120, lambda m: {"rain_today_mm": float(m)})
    deleted = purge(settings, T0 + 120 * 60)  # säilytys 60 min -> minuutit 0..59 pois
    assert deleted == 60
    conn = connect(settings.db_path)
    history = repo.hourly_history(conn, "house-1", "rain_today_mm", 0)
    remaining = conn.execute("SELECT COUNT(*) FROM readings").fetchone()[0]
    conn.close()
    assert remaining == 60
    assert history == [{"hour": "2026-10-17T07:00:00Z", "min": 0.0, "max": 59.0, "avg": 29.5, "count": 60}]


def test_rule_removed_resolves(settings, rules):
    feed(settings, 0, 61, rainy)
    evaluate_all(settings, rules, T0 + 60 * 60, full=True)
    remaining_rules = [r for r in rules if r.group_key != "rain"]
    events = evaluate_all(settings, remaining_rules, T0 + 61 * 60, full=True)
    resolved = [e for e in events if e["event_type"] == "resolved"]
    assert resolved and resolved[0]["alert"]["details"]["resolution_reason"] == "rule_removed"
