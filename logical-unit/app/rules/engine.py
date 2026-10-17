"""Deterministinen sääntömoottori.

Säännöt kuvataan YAML-tiedostossa (config/rules.yaml). Jokainen sääntö arvioidaan
mittausikkunaa vasten ja tulos on yksi kolmesta:

  FIRED   – ehto täyttyy, syntyy löydös (Finding)
  CLEAR   – dataa on riittävästi ja ehto EI täyty -> aktiivinen hälytys voidaan kuitata
  UNKNOWN – dataa ei ole tarpeeksi -> ei luoda eikä kuitata mitään

UNKNOWN on tärkeä: jos data lakkaa tulemasta, se ei saa kuitata hälytyksiä "kunnossa"-tilaan.
Kielimalli ei osallistu tähän päätökseen lainkaan.
"""

from __future__ import annotations

import math
import operator
from dataclasses import dataclass, field
from pathlib import Path
from statistics import fmean
from typing import Any, Callable

import yaml

SEVERITY_ORDER = {"info": 0, "low": 1, "medium": 2, "high": 3, "critical": 4}

OPERATORS: dict[str, Callable[[float, float], bool]] = {
    "<": operator.lt,
    "<=": operator.le,
    ">": operator.gt,
    ">=": operator.ge,
}

AGGREGATES: dict[str, Callable[[list[float]], float]] = {
    "avg": fmean,
    "min": min,
    "max": max,
    "last": lambda values: values[-1],
}

# Säännön parametrien oletusarvot tyypeittäin. Pakolliset parametrit ovat REQUIRED-listassa.
DEFAULTS: dict[str, dict[str, Any]] = {
    "threshold": {"window_minutes": 15, "aggregate": "avg", "min_points": 1},
    "change": {"window_minutes": 60, "compare_minutes": 10, "direction": "down"},
    "sustained": {"window_minutes": 60, "min_coverage": 0.8, "interval_seconds": 60},
    "flatline": {"window_minutes": 60, "min_points": 30, "tolerance": 0.0},
    "missing_data": {"max_gap_minutes": 10},
}
REQUIRED: dict[str, list[str]] = {
    "threshold": ["op", "value"],
    "change": ["pct"],
    "sustained": ["op", "value"],
    "flatline": [],
    "missing_data": [],
}
TOP_LEVEL_KEYS = {
    "id", "type", "severity", "message", "metric", "group", "category",
    "immediate", "sources", "description", "notify_on_value_change",
}

FIRED, CLEAR, UNKNOWN = "fired", "clear", "unknown"

Point = tuple[int, float]


class RuleConfigError(ValueError):
    pass


@dataclass(frozen=True)
class Rule:
    id: str
    type: str
    severity: str
    message: str
    metric: str | None = None
    group: str | None = None
    category: str | None = None
    immediate: bool = False
    notify_on_value_change: bool = True
    sources: frozenset[str] | None = None
    params: dict[str, Any] = field(default_factory=dict, hash=False, compare=False)

    @property
    def group_key(self) -> str:
        """Saman ryhmän säännöt muodostavat yhden hälytyksen (vakavin voittaa -> eskalointi)."""
        return self.group or self.id

    def fingerprint(self, source_id: str) -> str:
        return f"{self.group_key}:{source_id}"

    def applies_to(self, source_id: str) -> bool:
        return self.sources is None or source_id in self.sources

    @property
    def history_minutes(self) -> int:
        return int(self.params.get("window_minutes", 0))


@dataclass(frozen=True)
class Window:
    """Yhden lähteen mittaukset arviointihetkellä."""

    source_id: str
    now: int
    series: dict[str, list[Point]]  # metric -> [(ts, value)] aikajärjestyksessä
    last_seen: int | None = None

    def points(self, metric: str, minutes: float) -> list[Point]:
        since = self.now - minutes * 60
        return [p for p in self.series.get(metric, []) if since <= p[0] <= self.now]


@dataclass(frozen=True)
class Finding:
    rule: Rule
    source_id: str
    value: float | None
    details: dict[str, Any]

    @property
    def severity(self) -> str:
        return self.rule.severity

    @property
    def fingerprint(self) -> str:
        return self.rule.fingerprint(self.source_id)

    @property
    def message(self) -> str:
        context = {"source_id": self.source_id, "metric": self.rule.metric, "value": _fmt(self.value)}
        context.update({k: _fmt(v) for k, v in self.details.items()})
        return self.rule.message.format_map(_SafeDict(context))


@dataclass(frozen=True)
class Outcome:
    rule: Rule
    status: str  # FIRED / CLEAR / UNKNOWN
    finding: Finding | None = None


# ---------------------------------------------------------------- arvioijat
# Palauttavat UNKNOWN, CLEAR tai (value, details) kun ehto täyttyy.

def _threshold(rule: Rule, w: Window):
    p = rule.params
    pts = w.points(rule.metric, p["window_minutes"])
    if len(pts) < p["min_points"]:
        return UNKNOWN
    value = AGGREGATES[p["aggregate"]]([v for _, v in pts])
    if not OPERATORS[p["op"]](value, p["value"]):
        return CLEAR
    return value, {
        "aggregate": p["aggregate"], "op": p["op"], "threshold": p["value"],
        "window_minutes": p["window_minutes"], "points": len(pts),
    }


def _change(rule: Rule, w: Window):
    p = rule.params
    start = w.now - p["window_minutes"] * 60
    cmp = p["compare_minutes"] * 60
    series = w.series.get(rule.metric, [])
    baseline = [v for t, v in series if start <= t < start + cmp]
    current = [v for t, v in series if w.now - cmp < t <= w.now]
    if not baseline or not current:
        return UNKNOWN
    base, cur = fmean(baseline), fmean(current)
    if base == 0:
        return UNKNOWN
    pct = (cur - base) / abs(base) * 100
    hit = {
        "down": pct <= -p["pct"],
        "up": pct >= p["pct"],
        "any": abs(pct) >= p["pct"],
    }[p["direction"]]
    if not hit:
        return CLEAR
    return round(pct, 2), {
        "baseline": round(base, 4), "current": round(cur, 4),
        "change_pct": round(pct, 2), "abs_change_pct": round(abs(pct), 2), "limit_pct": p["pct"], "window_minutes": p["window_minutes"],
    }


def _sustained(rule: Rule, w: Window):
    p = rule.params
    pts = w.points(rule.metric, p["window_minutes"])
    expected = p["window_minutes"] * 60 / p["interval_seconds"]
    if len(pts) < math.ceil(expected * p["min_coverage"]):
        return UNKNOWN
    op = OPERATORS[p["op"]]
    values = [v for _, v in pts]
    if not all(op(v, p["value"]) for v in values):
        return CLEAR
    # Raportoidaan "lievin" arvo: esim. "> 0.5 koko tunnin" -> pienin havaittu arvo.
    value = min(values) if p["op"] in (">", ">=") else max(values)
    return value, {
        "op": p["op"], "threshold": p["value"], "points": len(pts),
        "duration_minutes": round((pts[-1][0] - pts[0][0]) / 60),
    }


def _flatline(rule: Rule, w: Window):
    p = rule.params
    pts = w.points(rule.metric, p["window_minutes"])
    if len(pts) < p["min_points"]:
        return UNKNOWN
    values = [v for _, v in pts]
    spread = max(values) - min(values)
    if spread > p["tolerance"]:
        return CLEAR
    return values[-1], {"spread": spread, "points": len(pts), "window_minutes": p["window_minutes"]}


def _missing_data(rule: Rule, w: Window):
    if w.last_seen is None:
        return UNKNOWN
    gap_minutes = (w.now - w.last_seen) / 60
    if gap_minutes <= rule.params["max_gap_minutes"]:
        return CLEAR
    return round(gap_minutes, 1), {
        "gap_minutes": round(gap_minutes, 1), "max_gap_minutes": rule.params["max_gap_minutes"],
    }


EVALUATORS = {
    "threshold": _threshold,
    "change": _change,
    "sustained": _sustained,
    "flatline": _flatline,
    "missing_data": _missing_data,
}


def evaluate(rule: Rule, window: Window) -> Outcome:
    result = EVALUATORS[rule.type](rule, window)
    if result in (UNKNOWN, CLEAR):
        return Outcome(rule, result)
    value, details = result
    return Outcome(rule, FIRED, Finding(rule, window.source_id, value, details))


# ---------------------------------------------------------------- lataus ja validointi

def load_rules(path: str | Path) -> list[Rule]:
    data = yaml.safe_load(Path(path).read_text(encoding="utf-8")) or {}
    raw_rules = data.get("rules")
    if not isinstance(raw_rules, list) or not raw_rules:
        raise RuleConfigError(f"{path}: 'rules'-listaa ei löytynyt tai se on tyhjä")
    rules: list[Rule] = []
    seen: set[str] = set()
    for index, raw in enumerate(raw_rules, start=1):
        label = raw.get("id") if isinstance(raw, dict) else None
        try:
            rule = parse_rule(raw)
        except (RuleConfigError, TypeError, ValueError) as exc:
            raise RuleConfigError(f"Sääntö #{index} ({label or '?'}): {exc}") from exc
        if rule.id in seen:
            raise RuleConfigError(f"Sääntö #{index}: id '{rule.id}' on jo käytössä")
        seen.add(rule.id)
        rules.append(rule)
    return rules


def parse_rule(raw: dict[str, Any]) -> Rule:
    if not isinstance(raw, dict):
        raise RuleConfigError("säännön pitää olla avain-arvo-rakenne")
    for key in ("id", "type", "severity", "message"):
        if not raw.get(key):
            raise RuleConfigError(f"kenttä '{key}' puuttuu")
    rule_type = raw["type"]
    if rule_type not in EVALUATORS:
        raise RuleConfigError(f"tuntematon tyyppi '{rule_type}', sallitut: {sorted(EVALUATORS)}")
    if raw["severity"] not in SEVERITY_ORDER:
        raise RuleConfigError(f"tuntematon severity '{raw['severity']}', sallitut: {list(SEVERITY_ORDER)}")

    metric = raw.get("metric")
    if rule_type == "missing_data":
        if metric:
            raise RuleConfigError("missing_data koskee koko lähdettä, poista 'metric'")
    elif not metric:
        raise RuleConfigError("kenttä 'metric' puuttuu")

    params = {k: v for k, v in raw.items() if k not in TOP_LEVEL_KEYS}
    allowed = set(DEFAULTS[rule_type]) | set(REQUIRED[rule_type])
    unknown = set(params) - allowed
    if unknown:
        raise RuleConfigError(f"tuntemattomat parametrit {sorted(unknown)}, sallitut: {sorted(allowed)}")
    missing = [k for k in REQUIRED[rule_type] if k not in params]
    if missing:
        raise RuleConfigError(f"pakolliset parametrit puuttuvat: {missing}")
    params = {**DEFAULTS[rule_type], **params}
    _validate_params(rule_type, params)

    sources = raw.get("sources")
    return Rule(
        id=str(raw["id"]),
        type=rule_type,
        severity=raw["severity"],
        message=str(raw["message"]),
        metric=metric,
        group=raw.get("group"),
        category=(raw.get("category") or None) and str(raw["category"]).lower(),
        immediate=bool(raw.get("immediate", False)),
        # Esim. "data puuttunut 70 min" kasvaa koko ajan; ei uutta ilmoitusta joka tunti.
        notify_on_value_change=bool(raw.get("notify_on_value_change", rule_type != "missing_data")),
        sources=frozenset(map(str, sources)) if sources else None,
        params=params,
    )


def _validate_params(rule_type: str, p: dict[str, Any]) -> None:
    if "op" in p and p["op"] not in OPERATORS:
        raise RuleConfigError(f"op '{p['op']}' ei kelpaa, sallitut: {list(OPERATORS)}")
    if "aggregate" in p and p["aggregate"] not in AGGREGATES:
        raise RuleConfigError(f"aggregate '{p['aggregate']}' ei kelpaa, sallitut: {list(AGGREGATES)}")
    if "direction" in p and p["direction"] not in ("down", "up", "any"):
        raise RuleConfigError("direction pitää olla down, up tai any")
    for key in ("value", "pct", "tolerance", "min_coverage", "max_gap_minutes"):
        if key in p and (isinstance(p[key], bool) or not isinstance(p[key], (int, float))):
            raise RuleConfigError(f"'{key}' pitää olla numero")
    for key in ("window_minutes", "compare_minutes", "min_points", "interval_seconds"):
        if key in p and (isinstance(p[key], bool) or not isinstance(p[key], int) or p[key] <= 0):
            raise RuleConfigError(f"'{key}' pitää olla positiivinen kokonaisluku")
    if rule_type == "change":
        if p["pct"] <= 0:
            raise RuleConfigError("'pct' pitää olla positiivinen (suunta annetaan direction-kentällä)")
        if p["compare_minutes"] * 2 > p["window_minutes"]:
            raise RuleConfigError("compare_minutes saa olla enintään puolet window_minutes-arvosta")
    if not 0 < p.get("min_coverage", 1) <= 1:
        raise RuleConfigError("min_coverage pitää olla välillä 0–1")


def validate_against_retention(rules: list[Rule], retention_minutes: int) -> None:
    too_long = [r.id for r in rules if r.history_minutes > retention_minutes]
    if too_long:
        raise RuleConfigError(
            f"Säännöt {too_long} tarvitsevat pidemmän historian kuin RETENTION_MINUTES={retention_minutes}"
        )


# ---------------------------------------------------------------- apurit

class _SafeDict(dict):
    def __missing__(self, key: str) -> str:
        return "{" + key + "}"


def _fmt(value: Any) -> Any:
    if isinstance(value, float):
        return f"{value:.2f}".rstrip("0").rstrip(".") if not value.is_integer() else str(int(value))
    return value
