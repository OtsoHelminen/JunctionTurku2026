import json

from app import repository as repo
from app.agent.worker import process_pending
from app.db import connect, session
from app.jobs import evaluate_all
from conftest import T0
from test_lifecycle import feed, low_pressure


class ScriptedClient:
    """Testiasiakas: palauttaa ennalta määrätyt vastaukset oikean mallin sijaan."""

    model = "scripted-test"

    def __init__(self, replies):
        self.replies = list(replies)
        self.calls = []

    def chat(self, messages, tools):
        self.calls.append(messages)
        reply = self.replies.pop(0)
        if isinstance(reply, Exception):
            raise reply
        return reply


def tool_call(name, args, call_id="c1"):
    return {"content": "", "tool_calls": [{"id": call_id, "type": "function",
            "function": {"name": name, "arguments": json.dumps(args)}}]}


def final(**kw):
    body = {"assessment": "Paine on laskenut tasaisesti.", "likely_cause": "Vuoto",
            "recommendation": "Tilaa putkiasentaja.", "urgency": "today",
            "suggested_resolver_ids": [], "confidence": "medium"}
    body.update(kw)
    return {"content": "<think>pohdintaa</think>\n```json\n" + json.dumps(body) + "\n```"}


def make_alert(settings, rules):
    feed(settings, 0, 61, low_pressure)
    evaluate_all(settings, rules, T0 + 60 * 60, full=True)


def first_active(settings):
    with session(settings.db_path) as conn:
        return {a["rule_id"]: a for a in repo.list_alerts(conn, "active", None, 10)}


def test_agent_uses_tools_and_drops_hallucinated_resolvers(settings, rules):
    make_alert(settings, rules)
    conn = connect(settings.db_path)
    putki_ids = [r["id"] for r in repo.find_resolvers(conn, "putki", "Helsinki")]
    conn.close()
    client = ScriptedClient([
        tool_call("get_recent_readings", {"metric": "water_pressure_bar", "minutes": 30}),
        tool_call("find_resolvers", {"category": "putki"}),
        final(suggested_resolver_ids=[putki_ids[0], 999]),
    ])
    process_pending(settings, client, now=T0 + 61 * 60, limit=1)

    analysis = first_active(settings)["pressure_low"]["analysis"]
    assert analysis["status"] == "done" and analysis["source"] == "llm"
    assert [r["id"] for r in analysis["suggested_resolvers"]] == [putki_ids[0]]
    assert analysis["suggested_resolvers"][0]["phone"]  # yhteystieto tulee kannasta
    assert analysis["dropped_resolver_ids"] == [999]
    tool_msgs = [m for m in client.calls[-1] if m["role"] == "tool"]
    assert "phone" not in tool_msgs[1]["content"]  # mallille ei annettu yhteystietoja


def test_agent_retries_on_invalid_json(settings, rules):
    make_alert(settings, rules)
    client = ScriptedClient([{"content": "En osaa sanoa."}, final()])
    process_pending(settings, client, now=T0 + 61 * 60, limit=1)
    assert first_active(settings)["pressure_low"]["analysis"]["status"] == "done"


def test_agent_failure_falls_back_to_playbook(settings, rules):
    make_alert(settings, rules)
    s = settings
    client = ScriptedClient([RuntimeError("yhteys katkesi")] * 3)
    now = T0 + 61 * 60
    for attempt in range(3):
        process_pending(s, client, now=now + attempt * 600, limit=1)
    analysis = first_active(s)["pressure_low"]["analysis"]
    assert analysis["status"] == "failed" and analysis["source"] == "playbook"
    assert analysis["playbook_actions"] and analysis["suggested_resolvers"]


def test_disabled_agent_uses_playbook(settings, rules):
    make_alert(settings, rules)
    process_pending(settings, None, now=T0 + 61 * 60, limit=10)
    analysis = first_active(settings)["pressure_low"]["analysis"]
    assert analysis["status"] == "skipped" and analysis["reason"] == "agent_disabled"
    assert analysis["suggested_resolvers"][0]["name"] == "Esimerkki Putkihuolto Oy"
