from dataclasses import replace

from app import repository as repo
from app.db import connect, session
from app.jobs import evaluate_all, minute_tick, purge
from conftest import T0


def feed(settings, minute_from, minute_to, metrics_fn, source="site-42", area="Helsinki"):
    with session(settings.db_path) as conn:
        for m in range(minute_from, minute_to):
            ts = T0 + m * 60
            repo.upsert_source(conn, source, area, ts)
            repo.insert_readings(conn, source, ts, metrics_fn(m))


def normal(m):
    return {"water_pressure_bar": 3.0 + (m % 3) * 0.01, "flow_l_min": 0.0, "temperature_c": 19.0}


def low_pressure(m):
    return {"water_pressure_bar": 1.7 + (m % 3) * 0.01, "flow_l_min": 0.0, "temperature_c": 19.0}


def types(events):
    return [(e["event_type"], e["alert"]["rule_id"]) for e in events]


def test_full_lifecycle(settings, rules):
    feed(settings, 0, 61, normal)
    assert evaluate_all(settings, rules, T0 + 60 * 60, full=True) == []

    # Paine putoaa tunnin puolivälissä -> pressure_low + pressure_drop
    feed(settings, 61, 91, normal)
    feed(settings, 91, 121, low_pressure)
    events = evaluate_all(settings, rules, T0 + 120 * 60, full=True)
    assert {("created", "pressure_low"), ("created", "pressure_drop")} <= set(types(events))

    # Sama tilanne jatkuu -> ei uusia hälytyksiä (pressure_drop kuittautuu, koska lasku on ohi)
    feed(settings, 121, 181, low_pressure)
    events = evaluate_all(settings, rules, T0 + 180 * 60, full=True)
    assert not any(t == "created" for t, _ in types(events))
    assert ("resolved", "pressure_drop") in types(events)

    # Kriittinen pudotus -> minuuttiajo eskaloi heti samaa hälytystä
    feed(settings, 181, 183, lambda m: {**low_pressure(m), "water_pressure_bar": 0.8})
    events = minute_tick(settings, rules, T0 + 182 * 60)
    assert types(events) == [("escalated", "pressure_critical")]

    with session(settings.db_path) as conn:
        alerts = repo.list_alerts(conn, "active", None, 50)
    pressure = [a for a in alerts if a["fingerprint"] == "water_pressure:site-42"]
    assert len(pressure) == 1 and pressure[0]["severity"] == "critical" and pressure[0]["revision"] == 2

    # Korjattu -> kuittaus tuntiajossa
    feed(settings, 183, 241, normal)
    events = evaluate_all(settings, rules, T0 + 240 * 60, full=True)
    assert ("resolved", "pressure_critical") in types(events)


def test_partial_evaluation_never_resolves(settings, rules):
    feed(settings, 0, 5, lambda m: {"water_pressure_bar": 0.5})
    assert types(minute_tick(settings, rules, T0 + 4 * 60)) == [("created", "pressure_critical")]
    feed(settings, 5, 10, lambda m: {"water_pressure_bar": 3.0})
    assert minute_tick(settings, rules, T0 + 9 * 60) == []
    with session(settings.db_path) as conn:
        assert len(repo.list_alerts(conn, "active", None, 10)) == 1


def test_missing_data_does_not_resolve_other_alerts(settings, rules):
    feed(settings, 0, 61, low_pressure)
    evaluate_all(settings, rules, T0 + 60 * 60, full=True)
    # Data loppuu kokonaan: paine-hälytys jää, no_data syntyy
    later = T0 + 180 * 60
    purge(settings, later)
    events = evaluate_all(settings, rules, later, full=True)
    assert types(events) == [("created", "no_data")]
    with session(settings.db_path) as conn:
        active = {a["rule_id"] for a in repo.list_alerts(conn, "active", None, 10)}
    assert {"pressure_low", "no_data"} <= active


def test_reminder_after_quiet_period(settings, rules):
    s = replace(settings, renotify_hours=2)
    feed(s, 0, 61, low_pressure)
    evaluate_all(s, rules, T0 + 60 * 60, full=True)
    feed(s, 61, 121, low_pressure)
    assert not any(t == "reminder" for t, _ in types(evaluate_all(s, rules, T0 + 120 * 60, full=True)))
    feed(s, 121, 181, low_pressure)
    assert ("reminder", "pressure_low") in types(evaluate_all(s, rules, T0 + 180 * 60, full=True))


def test_purge_keeps_hourly_summary(settings):
    feed(settings, 0, 120, lambda m: {"water_pressure_bar": float(m)})
    deleted = purge(settings, T0 + 120 * 60)  # säilytys 60 min -> minuutit 0..59 pois
    assert deleted == 60
    conn = connect(settings.db_path)
    history = repo.hourly_history(conn, "site-42", "water_pressure_bar", 0)
    remaining = conn.execute("SELECT COUNT(*) FROM readings").fetchone()[0]
    conn.close()
    assert remaining == 60
    assert history == [{"hour": "2026-10-17T07:00:00Z", "min": 0.0, "max": 59.0, "avg": 29.5, "count": 60}]


def test_rule_removed_resolves(settings, rules):
    feed(settings, 0, 61, low_pressure)
    evaluate_all(settings, rules, T0 + 60 * 60, full=True)
    remaining_rules = [r for r in rules if r.group_key != "water_pressure"]
    events = evaluate_all(settings, remaining_rules, T0 + 61 * 60, full=True)
    resolved = [e for e in events if e["event_type"] == "resolved"]
    assert resolved and resolved[0]["alert"]["details"]["resolution_reason"] == "rule_removed"
