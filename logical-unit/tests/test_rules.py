import pytest

from app.rules import CLEAR, FIRED, UNKNOWN, RuleConfigError, Window, evaluate
from app.rules.engine import parse_rule

NOW = 10_000_000


def window(metric, values, *, step=60, last_seen=None):
    """values[-1] on uusin piste hetkellä NOW."""
    n = len(values)
    series = [(NOW - (n - 1 - i) * step, float(v)) for i, v in enumerate(values)]
    return Window("site-1", NOW, {metric: series}, last_seen if last_seen is not None else NOW)


def rule(**kw):
    base = {"id": "r", "severity": "medium", "message": "{source_id}: {value}"}
    base.update(kw)
    return parse_rule(base)


def test_threshold_fires_clears_and_unknown():
    r = rule(type="threshold", metric="p", op="<", value=2.0, window_minutes=15, min_points=5)
    assert evaluate(r, window("p", [1.5] * 15)).status == FIRED
    assert evaluate(r, window("p", [2.5] * 15)).status == CLEAR
    assert evaluate(r, window("p", [1.5] * 3)).status == UNKNOWN


def test_threshold_message_formatting():
    r = rule(type="threshold", metric="p", op="<", value=2.0, message="paine {value} < {threshold}")
    out = evaluate(r, window("p", [1.25] * 5))
    assert out.finding.message == "paine 1.25 < 2"


def test_change_detects_drop():
    r = rule(type="change", metric="p", pct=25, window_minutes=60, compare_minutes=10)
    values = [3.0] * 30 + [2.0] * 31
    out = evaluate(r, window("p", values))
    assert out.status == FIRED
    assert out.finding.details["change_pct"] == pytest.approx(-33.33, abs=0.01)
    assert evaluate(r, window("p", [3.0] * 61)).status == CLEAR


def test_sustained_requires_coverage_and_all_points():
    r = rule(type="sustained", metric="f", op=">", value=0.5, window_minutes=60)
    assert evaluate(r, window("f", [2.0] * 61)).status == FIRED
    assert evaluate(r, window("f", [2.0] * 30 + [0.0] + [2.0] * 30)).status == CLEAR
    assert evaluate(r, window("f", [2.0] * 20)).status == UNKNOWN


def test_flatline():
    r = rule(type="flatline", metric="p", window_minutes=60, min_points=45)
    assert evaluate(r, window("p", [3.0] * 50)).status == FIRED
    assert evaluate(r, window("p", [3.0] * 49 + [3.1])).status == CLEAR


def test_missing_data():
    r = rule(type="missing_data", max_gap_minutes=10)
    assert evaluate(r, Window("s", NOW, {}, NOW - 15 * 60)).status == FIRED
    assert evaluate(r, Window("s", NOW, {}, NOW - 5 * 60)).status == CLEAR
    assert evaluate(r, Window("s", NOW, {}, None)).status == UNKNOWN


@pytest.mark.parametrize(
    "bad",
    [
        {"type": "nope", "metric": "p"},
        {"type": "threshold", "metric": "p", "op": "<"},                       # value puuttuu
        {"type": "threshold", "metric": "p", "op": "!", "value": 1},           # huono operaattori
        {"type": "threshold", "metric": "p", "op": "<", "value": 1, "windw_minutes": 5},  # kirjoitusvirhe
        {"type": "change", "metric": "p", "pct": -10},
        {"type": "missing_data", "metric": "p"},
    ],
)
def test_invalid_rules_are_rejected(bad):
    with pytest.raises(RuleConfigError):
        rule(**bad)


def test_shipped_rules_load(rules):
    assert {r.id for r in rules} >= {"heavy_rain", "extreme_rain", "storm_wind", "severe_storm", "flood_warning", "forest_fire_warning", "no_data"}
