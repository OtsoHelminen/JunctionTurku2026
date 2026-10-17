"""Qwen-agentti: rikastaa JO SYNTYNEEN hälytyksen arviolla, suosituksella ja ratkaisijaehdotuksella.

Turvarajat:
- Agentti ei luo, poista eikä kuittaa hälytyksiä.
- Työkalut ovat vain lukevia ja rajattu hälytyksen omaan lähteeseen.
- Ratkaisijaehdotukset suodatetaan: kelpaavat vain ne, jotka find_resolvers oikeasti palautti.
- Yhteystiedot haetaan kannasta, ei mallin tekstistä.
- Jos malli ei ole käytössä tai epäonnistuu, käytetään pelikirjaan perustuvaa varasuositusta.

Asiantuntijaehdotus (suggested_expert) on toistaiseksi mallin tai pelikirjan antama ESIMERKKI
hinta-arvioineen, ei rekisteröity kumppani (registered = false). Myöhemmin tilalle tulee
kumppanitietokannasta haettu yritys.
"""

from __future__ import annotations

import json
import re
import sqlite3
from typing import Any, Literal

from pydantic import BaseModel, Field, ValidationError, model_validator

from .. import repository as repo
from ..config import Settings
from ..serializers import alert_to_dict, iso
from .llm import ChatClient

SYSTEM_PROMPT = """You are a weather-risk analyst for residential properties.
The rule engine has already determined from the weather forecast that the alert is justified. Do not question it.
You receive the alert and the property details (construction year, renovations, house type, condition). Your task:
1. assess what risk the forecast weather poses to this specific property (use the tools to fetch data),
2. state the most likely damage mechanism (e.g. roof leak, basement flooding, frozen pipes),
3. recommend one concrete preventive action,
4. suggest a resolver ONLY from those returned by the find_resolvers tool (use their id numbers),
5. suggest the type of expert who should do the work, with an illustrative example company and a price estimate.
Do not invent resolver ids, contact details or measurements. If the data is insufficient, say so and lower the confidence.

The expert is an illustrative suggestion, not a real partner: example_name must be clearly fictional
(e.g. "Example Roofing Ltd") and must not resemble a real company. Estimate the price for this job in euros,
including VAT, at typical Finnish market rates, and say in price_basis what the estimate covers.

When you are done, reply with ONLY a JSON object and no other text:
{"assessment": "...", "likely_cause": "...", "recommendation": "...",
 "urgency": "immediate|today|this_week|monitor", "suggested_resolver_ids": [1],
 "confidence": "low|medium|high",
 "expert": {"profession": "...", "example_name": "...", "reason": "...",
            "price_min_eur": 200, "price_max_eur": 600, "price_basis": "..."}}
Write the text fields in English, briefly and factually."""

TOOLS: list[dict[str, Any]] = [
    {
        "type": "function",
        "function": {
            "name": "get_recent_readings",
            "description": "Per-minute readings of one metric for the alert's property over the last minutes (at most 60 min).",
            "parameters": {
                "type": "object",
                "properties": {
                    "metric": {"type": "string", "description": "Metric name, e.g. rain_today_mm, wind_today_m_s, temp_min_today_c"},
                    "minutes": {"type": "integer", "minimum": 1, "maximum": 60},
                },
                "required": ["metric"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_hourly_history",
            "description": "Hourly aggregates (min, max, avg) of one metric for the alert's property, up to 168 h back.",
            "parameters": {
                "type": "object",
                "properties": {
                    "metric": {"type": "string"},
                    "hours": {"type": "integer", "minimum": 1, "maximum": 168},
                },
                "required": ["metric"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "find_resolvers",
            "description": "Finds resolver partners by category (roof, moisture = moisture/flooding, plumbing = plumbing/heating, fire, automation) in the alert's area.",
            "parameters": {
                "type": "object",
                "properties": {"category": {"type": "string"}},
                "required": ["category"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_playbook",
            "description": "Returns the standard actions for the alert rule, the recommended resolver category and a reference expert with a typical price range.",
            "parameters": {"type": "object", "properties": {}},
        },
    },
]

_THINK_RE = re.compile(r"<think>.*?</think>", re.DOTALL)  # Qwen3:n ajatteluosio pois


class AgentError(RuntimeError):
    pass


class ExpertSuggestion(BaseModel):
    profession: str = Field(min_length=1, max_length=200)
    example_name: str = Field(min_length=1, max_length=200)
    reason: str | None = Field(default=None, max_length=1000)
    price_min_eur: int = Field(ge=0, le=1_000_000)
    price_max_eur: int = Field(ge=0, le=1_000_000)
    price_basis: str | None = Field(default=None, max_length=500)

    @model_validator(mode="after")
    def _price_range(self) -> "ExpertSuggestion":
        if self.price_min_eur > self.price_max_eur:
            raise ValueError("price_min_eur must not exceed price_max_eur")
        return self


class AgentOutput(BaseModel):
    assessment: str = Field(min_length=1, max_length=2000)
    likely_cause: str | None = Field(default=None, max_length=1000)
    recommendation: str = Field(min_length=1, max_length=2000)
    urgency: Literal["immediate", "today", "this_week", "monitor"]
    suggested_resolver_ids: list[int] = Field(default_factory=list, max_length=5)
    confidence: Literal["low", "medium", "high"]
    expert: ExpertSuggestion | None = None


def analyze_alert(
    conn: sqlite3.Connection, alert_row: sqlite3.Row, client: ChatClient, settings: Settings, now: int
) -> dict[str, Any]:
    alert = alert_to_dict(alert_row)
    alert.pop("analysis", None)
    messages: list[dict[str, Any]] = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": "Alert:\n" + json.dumps(alert, ensure_ascii=False, indent=2)
            + "\n\nProperty:\n" + json.dumps(repo.get_estate(conn, alert_row["source_id"]) or {}, ensure_ascii=False, indent=2)},
    ]
    offered_ids: set[int] = set()

    for _ in range(settings.agent_max_steps):
        reply = client.chat(messages, TOOLS)
        tool_calls = reply.get("tool_calls") or []
        if tool_calls:
            messages.append({"role": "assistant", "content": reply.get("content") or "", "tool_calls": tool_calls})
            for call in tool_calls:
                name = call.get("function", {}).get("name", "")
                args = _parse_args(call.get("function", {}).get("arguments"))
                result = _run_tool(conn, name, args, alert_row, settings, now)
                if name == "find_resolvers" and isinstance(result, list):
                    offered_ids.update(r["id"] for r in result)
                messages.append({
                    "role": "tool",
                    "tool_call_id": call.get("id", name),
                    "name": name,
                    "content": json.dumps(result, ensure_ascii=False),
                })
            continue

        content = reply.get("content") or ""
        try:
            output = _parse_output(content)
        except (ValueError, ValidationError) as exc:
            messages.append({"role": "assistant", "content": content})
            messages.append({
                "role": "user",
                "content": f"The reply was not valid ({str(exc)[:300]}). Return only the JSON object in the requested format.",
            })
            continue
        return _build_analysis(conn, alert_row, output, offered_ids, client.model, now)

    raise AgentError(f"agent gave no valid answer in {settings.agent_max_steps} steps")


def fallback_analysis(conn: sqlite3.Connection, alert_row: sqlite3.Row, now: int, reason: str) -> dict[str, Any]:
    """Deterministinen suositus pelikirjasta: toimii aina, myös ilman kielimallia."""
    playbook = repo.get_playbook(conn, alert_row["rule_id"])
    category = playbook["category"] if playbook else alert_row["category"]
    resolvers = repo.find_resolvers(conn, category, alert_row["area"], limit=3) if category else []
    actions = playbook["actions"] if playbook else []
    return {
        "source": "playbook",
        "reason": reason,
        "assessment": None,
        "likely_cause": None,
        "recommendation": actions[0] if actions else None,
        "urgency": "immediate" if alert_row["severity"] == "critical" else None,
        "confidence": None,
        "playbook_actions": actions,
        "suggested_resolvers": resolvers,
        "suggested_expert": _playbook_expert(playbook),
        "generated_at": iso(now),
    }


def _expert_dict(expert: ExpertSuggestion, source: str) -> dict[str, Any]:
    """Appille menevä muoto. registered=false: esimerkki, ei kumppanitietokannan yritys."""
    return {
        "registered": False,
        "source": source,
        "profession": expert.profession,
        "example_name": expert.example_name,
        "reason": expert.reason,
        "price_estimate": {
            "min_eur": expert.price_min_eur,
            "max_eur": expert.price_max_eur,
            "currency": "EUR",
            "includes_vat": True,
            "basis": expert.price_basis,
        },
    }


def _playbook_expert(playbook: dict[str, Any] | None) -> dict[str, Any] | None:
    if not playbook or not playbook.get("expert"):
        return None
    try:
        return _expert_dict(ExpertSuggestion.model_validate(playbook["expert"]), "playbook")
    except ValidationError:
        return None


# ---------------------------------------------------------------- sisäiset

def _run_tool(
    conn: sqlite3.Connection, name: str, args: dict[str, Any], alert_row: sqlite3.Row, settings: Settings, now: int
) -> Any:
    source_id = alert_row["source_id"]  # työkalut rajattu hälytyksen omaan lähteeseen
    try:
        if name == "get_recent_readings":
            minutes = _clamp(args.get("minutes", 60), 1, settings.retention_minutes)
            return repo.recent_readings(conn, source_id, str(args["metric"]), now - minutes * 60)
        if name == "get_hourly_history":
            hours = _clamp(args.get("hours", 24), 1, 168)
            return repo.hourly_history(conn, source_id, str(args["metric"]), now - hours * 3600)
        if name == "find_resolvers":
            # Mallille ei anneta yhteystietoja; ne liitetään vastaukseen kannasta.
            return repo.find_resolvers(conn, str(args["category"]), alert_row["area"], with_contact=False)
        if name == "get_playbook":
            return repo.get_playbook(conn, alert_row["rule_id"]) or {"info": "no playbook for this rule"}
        return {"error": f"unknown tool {name!r}"}
    except KeyError as exc:
        return {"error": f"missing parameter {exc}"}


def _build_analysis(
    conn: sqlite3.Connection,
    alert_row: sqlite3.Row,
    output: AgentOutput,
    offered_ids: set[int],
    model: str,
    now: int,
) -> dict[str, Any]:
    requested = list(dict.fromkeys(output.suggested_resolver_ids))
    known = repo.resolvers_by_ids(conn, [i for i in requested if i in offered_ids])
    kept = [known[i] for i in requested if i in known]
    dropped = [i for i in requested if i not in known]
    playbook = repo.get_playbook(conn, alert_row["rule_id"])
    analysis = {
        "source": "llm",
        "model": model,
        "assessment": output.assessment,
        "likely_cause": output.likely_cause,
        "recommendation": output.recommendation,
        "urgency": output.urgency,
        "confidence": output.confidence,
        "playbook_actions": playbook["actions"] if playbook else [],
        "suggested_resolvers": kept,
        # Mallin oma ehdotus; jos se puuttuu, pelikirjan esimerkki.
        "suggested_expert": _expert_dict(output.expert, "llm") if output.expert else _playbook_expert(playbook),
        "generated_at": iso(now),
    }
    if dropped:
        analysis["dropped_resolver_ids"] = dropped  # malli ehdotti jotain, mitä sille ei tarjottu
    return analysis


def _parse_output(content: str) -> AgentOutput:
    text = _THINK_RE.sub("", content).strip()
    start, end = text.find("{"), text.rfind("}")
    if start == -1 or end <= start:
        raise ValueError("no JSON object found")
    return AgentOutput.model_validate(json.loads(text[start : end + 1]))


def _parse_args(raw: Any) -> dict[str, Any]:
    if isinstance(raw, dict):
        return raw
    if isinstance(raw, str) and raw.strip():
        try:
            parsed = json.loads(raw)
            return parsed if isinstance(parsed, dict) else {}
        except json.JSONDecodeError:
            return {}
    return {}


def _clamp(value: Any, low: int, high: int) -> int:
    try:
        number = int(value)
    except (TypeError, ValueError):
        number = high
    return max(low, min(high, number))
