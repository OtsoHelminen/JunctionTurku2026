

#!/usr/bin/env python3
"""Simple interactive CLI for the weather/house API. No extra packages needed.

Usage: python cli.py [--url http://localhost:8008]
       (or set API_URL env var)
"""
import argparse
import json
import os
import urllib.error
import urllib.parse
import urllib.request

BASE = "http://localhost:8008"


def call(method, path, body=None, params=None):
    url = BASE.rstrip("/") + path
    if params:
        url += "?" + urllib.parse.urlencode(params)
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(url, data=data, method=method)
    if data is not None:
        req.add_header("Content-Type", "application/json")
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            raw = r.read().decode()
            print(f"\n[{r.status}]")
    except urllib.error.HTTPError as e:
        raw = e.read().decode()
        print(f"\n[{e.code} error]")
    except urllib.error.URLError as e:
        print(f"\nCould not reach {url}: {e.reason}")
        return
    if raw:
        try:
            print(json.dumps(json.loads(raw), indent=2, ensure_ascii=False))
        except ValueError:
            print(raw)
    else:
        print("(no content)")


def ask(label, cast=str, required=False, default=None):
    while True:
        hint = f" [{default}]" if default is not None else (
            "" if required else " (optional)")
        v = input(f"  {label}{hint}: ").strip()
        if not v:
            if default is not None:
                return default
            if not required:
                return None
            print("  Required.")
            continue
        try:
            return cast(v)
        except ValueError:
            print(f"  Invalid value, expected {cast.__name__}.")


def ask_payload():
    print("  Notification (Enter for defaults)")
    p = {
        "title": ask("title", default="Data updated"),
        "body": ask("body", default="New data is available."),
        "sound": ask("sound", default="default"),
    }
    d = ask("data as JSON, e.g. {\"k\": 1}")
    if d:
        try:
            p["data"] = json.loads(d)
        except ValueError:
            print("  Invalid JSON, ignoring data.")
    return p


def create_house():
    body = {
        "user_id": ask("user_id", required=True),
        "address": ask("address", required=True),
        "latitude": ask("latitude", float, required=True),
        "longitude": ask("longitude", float, required=True),
        "construction_year": ask("construction_year", int),
        "house_type": ask("house_type"),
        "floor_area_m2": ask("floor_area_m2", float),
        "number_of_floors": ask("number_of_floors", int),
        "condition": ask("condition"),
    }
    call("POST", "/app/houses", {k: v for k,
         v in body.items() if v is not None})


def register_device():
    token = ask("Expo token (ExponentPushToken[...])", required=True)
    platform = ask("platform ios/android")
    body = {"token": token}
    if platform:
        body["platform"] = platform
    call("POST", "/app/devices", body)


def simulate_event():
    print("\n  Simulate event:")
    print("   1. Storm")
    print("   2. Forest fire")
    print("   3. Frost")
    c = input("  > ").strip()
    paths = {
        "1": "/app/simulate/storm",
        "2": "/app/simulate/forest_fire",
        "3": "/app/simulate/frost",
    }
    if c in paths:
        call("GET", paths[c])
    else:
        print("  Unknown choice.")


MENU = [
    ("Get all weather events", lambda: call("GET", "/app/data_events")),
    ("Get events for a house", lambda: call(
        "GET", f"/app/data_events/{ask('house_id', int, True)}")),
    ("List houses", lambda: call("GET", "/app/houses")),
    ("Create house", create_house),
    ("Simulate event", simulate_event),
    ("Register device", register_device),
    ("List devices (all stored tokens)", lambda: call("GET", "/app/devices")),
    ("Unregister device", lambda: call("DELETE", "/app/devices",
     params={"token": ask("token", required=True)})),
    ("Notify one device", lambda: call("POST", "/app/notify/" +
     urllib.parse.quote(ask("token", required=True), safe=""), ask_payload())),
    ("Notify all devices", lambda: call("POST", "/app/notify", ask_payload())),
    ("Custom request", lambda: call(ask("method", default="GET").upper(), ask("path", required=True),
                                    json.loads(ask("JSON body") or "null"))),
]


def main():
    global BASE
    ap = argparse.ArgumentParser()
    ap.add_argument("--url", default=os.environ.get("API_URL", BASE))
    BASE = ap.parse_args().url
    while True:
        print(f"\n=== API CLI ({BASE}) ===")
        for i, (name, _) in enumerate(MENU, 1):
            print(f" {i:2}. {name}")
        print("  u. Change base URL\n  q. Quit")
        c = input("> ").strip().lower()
        if c in ("q", "quit", "exit"):
            break
        if c == "u":
            BASE = ask("base URL", default=BASE)
            continue
        if c.isdigit() and 1 <= int(c) <= len(MENU):
            try:
                MENU[int(c) - 1][1]()
            except (KeyboardInterrupt, EOFError):
                print("\n  Cancelled.")
            except ValueError as e:
                print(f"  Error: {e}")
        else:
            print("  Unknown choice.")


if __name__ == "__main__":
    try:
        main()
    except (KeyboardInterrupt, EOFError):
        print()
