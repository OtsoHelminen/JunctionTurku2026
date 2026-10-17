"""Qwen-agentti: rikastaa JO SYNTYNEEN hälytyksen arviolla, suosituksella ja ratkaisijaehdotuksella.

Turvarajat:
- Agentti ei luo, poista eikä kuittaa hälytyksiä.
- Työkalut ovat vain lukevia ja rajattu hälytyksen omaan lähteeseen.
- Ratkaisijaehdotukset suodatetaan: kelpaavat vain ne, jotka find_resolvers oikeasti palautti.
- Yhteystiedot haetaan kannasta, ei mallin tekstistä.
- Jos malli ei ole käytössä tai epäonnistuu, käytetään pelikirjaan perustuvaa varasuositusta.
"""

from __future__ import annotations

import json
import re
import sqlite3
from typing import Any, Literal

from pydantic import BaseModel, Field, ValidationError

from .. import repository as repo
from ..config import Settings
from ..serializers import alert_to_dict, iso
from .llm import ChatClient

SYSTEM_PROMPT = """Olet kiinteistöjen sääriskien analyytikko.
Sääntömoottori on jo todennut hälytyksen aiheelliseksi sääennusteen perusteella. Älä kyseenalaista sitä.
Saat hälytyksen ja kohteen tiedot (rakennusvuosi, remontit, talotyyppi, kunto). Tehtäväsi:
1. arvioi, mitä riskiä ennustettu sää aiheuttaa juuri tälle kohteelle (käytä työkaluja datan hakemiseen),
2. kerro todennäköisin vahinkomekanismi (esim. katon vuoto, kellarin tulviminen, putkien jäätyminen),
3. suosittele konkreettinen ennaltaehkäisevä toimenpide,
4. ehdota ratkaisijaa VAIN find_resolvers-työkalun palauttamista (käytä niiden id-numeroita).
Älä keksi ratkaisijoita, yhteystietoja tai mittausarvoja. Jos data ei riitä, sano se ja laske confidence-arvoa.

Kun olet valmis, vastaa PELKÄLLÄ JSON-objektilla ilman muuta tekstiä:
{"assessment": "...", "likely_cause": "...", "recommendation": "...",
 "urgency": "immediate|today|this_week|monitor", "suggested_resolver_ids": [1],
 "confidence": "low|medium|high"}
Kirjoita tekstikentät suomeksi, lyhyesti ja asiallisesti."""

TOOLS: list[dict[str, Any]] = [
    {
        "type": "function",
        "function": {
            "name": "get_recent_readings",
            "description": "Hälytyksen kohteen minuuttilukemat yhdelle mittarille viimeisten minuuttien ajalta (enintään 60 min).",
            "parameters": {
                "type": "object",
                "properties": {
                    "metric": {"type": "string", "description": "Mittarin nimi, esim. rain_today_mm, wind_today_m_s, temp_min_today_c"},
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
            "description": "Hälytyksen kohteen tuntikoosteet (min, max, keskiarvo) yhdelle mittarille, enintään 168 h taaksepäin.",
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
            "description": "Hakee ratkaisijakumppanit kategorialla (esim. katto, kosteus, lvi, automaatio) hälytyksen alueelta.",
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
            "description": "Hakee hälytyssäännön vakiotoimenpiteet ja suositellun ratkaisijakategorian.",
            "parameters": {"type": "object", "properties": {}},
        },
    },
]

_THINK_RE = re.compile(r"<think>.*?</think>", re.DOTALL)  # Qwen3:n ajatteluosio pois


class AgentError(RuntimeError):
    pass


class AgentOutput(BaseModel):
    assessment: str = Field(min_length=1, max_length=2000)
    likely_cause: str | None = Field(default=None, max_length=1000)
    recommendation: str = Field(min_length=1, max_length=2000)
    urgency: Literal["immediate", "today", "this_week", "monitor"]
    suggested_resolver_ids: list[int] = Field(default_factory=list, max_length=5)
    confidence: Literal["low", "medium", "high"]


def analyze_alert(
    conn: sqlite3.Connection, alert_row: sqlite3.Row, client: ChatClient, settings: Settings, now: int
) -> dict[str, Any]:
    alert = alert_to_dict(alert_row)
    alert.pop("analysis", None)
    messages: list[dict[str, Any]] = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": "Hälytys:\n" + json.dumps(alert, ensure_ascii=False, indent=2)
            + "\n\nKohde:\n" + json.dumps(repo.get_estate(conn, alert_row["source_id"]) or {}, ensure_ascii=False, indent=2)},
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
                "content": f"Vastaus ei ollut kelvollinen ({str(exc)[:300]}). Palauta pelkkä JSON-objekti pyydetyssä muodossa.",
            })
            continue
        return _build_analysis(conn, alert_row, output, offered_ids, client.model, now)

    raise AgentError(f"agentti ei antanut kelvollista vastausta {settings.agent_max_steps} askeleessa")


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
        "generated_at": iso(now),
    }


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
            return repo.get_playbook(conn, alert_row["rule_id"]) or {"info": "tälle säännölle ei ole pelikirjaa"}
        return {"error": f"tuntematon työkalu {name!r}"}
    except KeyError as exc:
        return {"error": f"puuttuva parametri {exc}"}


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
        "generated_at": iso(now),
    }
    if dropped:
        analysis["dropped_resolver_ids"] = dropped  # malli ehdotti jotain, mitä sille ei tarjottu
    return analysis


def _parse_output(content: str) -> AgentOutput:
    text = _THINK_RE.sub("", content).strip()
    start, end = text.find("{"), text.rfind("}")
    if start == -1 or end <= start:
        raise ValueError("JSON-objektia ei löytynyt")
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
