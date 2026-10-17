# Logical Unit – API

Logical Unit hakee sääennusteet Data Consolidatorilta ja tunnistaa kohteisiin kohdistuvat
sääriskit. Jokainen hälytys saa Qwen-mallin arvion ja ratkaisijaehdotuksen (tai pelikirjan
vakiosuosituksen, jos malli ei ole käytössä).

Hälytykset **lähetetään Appiin automaattisesti push-ilmoituksina** consolidatorin
`POST /app/notify` -rajapinnan kautta (ks. [Push-ilmoitukset](#push-ilmoitukset-appiin)).
Lisäksi ne ovat luettavissa HTTP-rajapinnasta, esim. kun App avataan ja se haluaa nykytilan.

```
Data Consolidator ──säädata──▶ Logical Unit ──hälytys──▶ Data Consolidator /app/notify ──Expo──▶ App
```

Oletusosoite: `http://localhost:8001`. Kaikki aikaleimat ovat ISO 8601 -muotoa UTC:nä (`2026-10-17T10:05:00Z`).

## Käynnistys

```bash
# terminaali 1: Data Consolidator (portti 8008)
cd data_consolidator && uv run uvicorn main:app --host 0.0.0.0 --port 8008

# terminaali 2: Logical Unit (portti 8001)
cd logical-unit
set -a && . ./.env && set +a          # Qwen-asetukset, ks. "Asetukset"
uv run uvicorn app.main:app --port 8001
```

Aja yhdellä prosessilla (ei `--workers`), muuten ajastimet käynnistyvät moneen kertaan.

## Push-ilmoitukset Appiin

Kun hälytys syntyy, pahenee, saa analyysin tai kuittautuu, Logical Unit lähettää muutaman
sekunnin sisällä ilmoituksen consolidatorille, joka välittää sen Expon kautta kaikille
laitteille, jotka App on rekisteröinyt (`POST /app/devices`). Appin ei tarvitse kysellä mitään.

Lähetettävä runko (consolidatorin `NotificationPayload`):

```json
{
  "title": "Kriittinen hälytys – Helsinki",
  "body": "Kova myrsky kohteessa house-1: tuuli 24.5 m/s",
  "sound": "default",
  "data": {
    "kind": "alert",
    "event_id": 7,
    "event_type": "created",
    "alert_id": 3,
    "fingerprint": "wind:house-1",
    "rule_id": "severe_storm",
    "source_id": "house-1",
    "house_id": 1,
    "area": "Helsinki",
    "severity": "critical",
    "category": "katto",
    "status": "active",
    "message": "Kova myrsky kohteessa house-1: tuuli 24.5 m/s",
    "recommendation": null,
    "urgency": null,
    "expert": null,
    "created_at": "2026-10-17T10:05:00Z"
  }
}
```

`analyzed`-ilmoituksessa `data.expert` sisältää asiantuntijaehdotuksen (ks. [`suggested_expert`](#suggested_expert)):

```json
"expert": {"registered": false, "profession": "Roofer", "example_name": "Example Roofing Ltd",
           "price_min_eur": 200, "price_max_eur": 600}
```

**Näin App tunnistaa ilmoituksen:** `data.kind == "alert"`. Saman hälytyksen ilmoituksilla on
sama `alert_id`, joten App voi päivittää olemassa olevaa hälytystä uuden luomisen sijaan.
`house_id` on consolidatorin talon id.

| `data.event_type` | Otsikko | Runko |
|---|---|---|
| `created` | `<Vakavuus> hälytys – <alue>` | hälytyksen viesti |
| `escalated` | `Hälytys paheni: <Vakavuus> – <alue>` | hälytyksen viesti |
| `analyzed` | `Toimenpidesuositus – <alue>` | Qwenin tai pelikirjan suositus (myös `data.recommendation`) ja rivi `Suggested expert: <ammatti>, approx. <min>–<max> €` |
| `resolved` | `Tilanne ohi – <alue>` | hälytyksen viesti, ei ääntä |

Vakavuus suomeksi: Tiedote, Vähäinen, Kohtalainen, Vakava, Kriittinen.

**Toimitusvarmuus:** lähettäjä etenee hälytysvirtaa (`alert_events`) kursorilla, joka tallentuu
kantaan. Jos consolidator ei vastaa, ilmoitus yritetään uudelleen, eikä mitään katoa. Pysyvästi
epäonnistuva ilmoitus ohitetaan `NOTIFY_MAX_ATTEMPTS` yrityksen jälkeen. Käynnistyksessä vanhoja
tapahtumia ei lähetetä uudelleen.

**Huom:** consolidatorin laitetokeneita ei ole sidottu käyttäjiin, joten `/app/notify` lähettää
ilmoituksen kaikille rekisteröidyille laitteille.

## Rajapinnat

| Metodi | Polku | Kuvaus |
|---|---|---|
| GET | [`/health`](#get-health) | palvelun tila |
| GET | [`/alerts`](#get-alerts) | hälytysten nykytila |
| GET | [`/alerts/{alert_id}`](#get-alertsalert_id) | yksittäinen hälytys |
| GET | [`/events`](#get-events) | hälytysvirta kursorilla (samat tapahtumat kuin push-ilmoituksissa) |
| POST | [`/input`](#post-input) | kohdedata käsin (normaalisti haetaan automaattisesti) |
| POST | [`/admin/evaluate`](#post-adminevaluate) | kaikkien sääntöjen arviointi heti (testaus) |

Interaktiivinen dokumentaatio: `http://localhost:8001/docs`.

### GET /health

```bash
curl localhost:8001/health
```

```json
{"status": "ok", "rules": 13, "agent_enabled": true, "model": "qwen3.8-flash"}
```

### GET /alerts

Hälytysten nykytila, vakavimmat ensin.

| Parametri | Oletus | Kuvaus |
|---|---|---|
| `status` | `active` | `active`, `resolved` tai `all` |
| `updated_after` | – | vain tämän jälkeen muuttuneet, esim. `2026-10-17T10:00:00Z` |
| `limit` | 100 | 1–500 |

```bash
curl "localhost:8001/alerts?status=active"
```

```json
{"alerts": [ { ...hälytys... }, ... ]}
```

### GET /alerts/{alert_id}

```bash
curl localhost:8001/alerts/3
```

Palauttaa yhden [hälytyksen](#hälytyksen-muoto) tai `404`, jos sitä ei ole.

### GET /events

Hälytysvirta: jokainen hälytyksen syntyminen, muutos, analyysi ja kuittaus on oma tapahtumansa.
Push-ilmoitukset tulevat samasta virrasta. Rajapinnalla App voi hakea välistä jääneet
tapahtumat, esim. jos laite oli pois päältä.

| Parametri | Oletus | Kuvaus |
|---|---|---|
| `after_id` | 0 | palauttaa tapahtumat, joiden `event_id` on tätä suurempi |
| `limit` | 100 | 1–500 |

```bash
curl "localhost:8001/events?after_id=0"
```

```json
{
  "events": [
    {
      "event_id": 12,
      "event_type": "escalated",
      "created_at": "2026-10-17T10:05:00Z",
      "alert": { ...hälytys tapahtumahetkellä... }
    }
  ],
  "last_id": 12
}
```

Tallenna `last_id` ja käytä sitä seuraavassa kyselyssä `after_id`:nä. Jos tapahtumia ei ole,
`events` on tyhjä ja `last_id` on sama kuin annettu `after_id`.

| `event_type` | Milloin | Push-ilmoitus (oletus) |
|---|---|---|
| `created` | uusi hälytys | kyllä |
| `escalated` | vakavuus nousi (esim. high → critical) | kyllä |
| `changed` | vakavuus laski tai arvo muuttui ≥ 10 % | ei |
| `analyzed` | Qwenin analyysi tai pelikirjasuositus valmistui | kyllä |
| `reminder` | tilanne jatkunut ennallaan 6 h | ei |
| `resolved` | ehto ei enää täyty | kyllä (tilanne ohi) |

Esimerkki välistä jääneiden tapahtumien hausta (Python):

```python
import time, httpx

last_id = 0
while True:
    data = httpx.get("http://localhost:8001/events", params={"after_id": last_id}).json()
    for event in data["events"]:
        alert = event["alert"]
        print(event["event_type"], alert["severity"], alert["message"])
    last_id = data["last_id"]
    time.sleep(10)
```

### POST /input

Normaalisti Logical Unit hakee datan itse Data Consolidatorilta minuutin välein. Tällä
rajapinnalla dataa voi syöttää käsin, esim. testissä. Runko on sama kuin consolidatorin
`GET /app/data_events/{house_id}` -vastaus (yksi kohde tai lista, ≤ 1000), ks. `examples/input.json`.

```bash
curl -X POST localhost:8001/input -H "Content-Type: application/json" -d @examples/input.json
```

```json
{"accepted_readings": 9, "houses_without_events": 0}
```

Yli 60 min vanhat ja yli 5 min tulevaisuudessa olevat tapahtumat ohitetaan. Puuttuva aikaleima
tulkitaan vastaanottohetkeksi.

### POST /admin/evaluate

Arvioi kaikki säännöt heti tasatuntia odottamatta. Käytössä vain, kun palvelu käynnistetään
asetuksella `ENABLE_ADMIN_ENDPOINTS=true`, muuten `404`.

```bash
curl -X POST localhost:8001/admin/evaluate
```

```json
{"events": [ { ...tapahtuma... }, ... ]}
```

## Hälytyksen muoto

```json
{
  "alert_id": 3,
  "fingerprint": "rain:house-1",
  "rule_id": "extreme_rain",
  "source_id": "house-1",
  "area": "Helsinki",
  "severity": "critical",
  "category": "kosteus",
  "status": "active",
  "message": "Erittäin rankka sade kohteessa house-1: ennuste 30 mm tänään, tulvariski",
  "value": 30.0,
  "details": {"aggregate": "last", "op": ">=", "threshold": 25, "window_minutes": 5, "points": 5},
  "revision": 2,
  "first_seen": "2026-10-17T10:00:00Z",
  "last_seen": "2026-10-17T10:05:00Z",
  "last_notified": "2026-10-17T10:05:00Z",
  "resolved_at": null,
  "updated_at": "2026-10-17T10:05:31Z",
  "analysis": {
    "status": "done",
    "source": "llm",
    "model": "qwen3.8-flash",
    "assessment": "The basement and drainage of this 1978 detached house are vulnerable...",
    "likely_cause": "Heavy rain exceeds the capacity of the drains and stormwater system...",
    "recommendation": "Move valuables out of the basement and check the flood pump...",
    "urgency": "immediate",
    "confidence": "medium",
    "playbook_actions": [
      "Move valuables from the basement and ground-level rooms to higher floors",
      "Check the drainage wells and that the flood pump (if any) works"
    ],
    "suggested_resolvers": [
      {
        "id": 6, "name": "Salaojat ja Tulvasuojaus Esimerkki Oy", "category": "kosteus",
        "areas": ["Helsinki", "Espoo", "Vantaa"], "on_call": true, "priority": 5,
        "notes": "On-call flood pumps and sandbags",
        "phone": "+358 40 000 0007", "email": "salaoja@example.com"
      }
    ],
    "suggested_expert": {
      "registered": false,
      "source": "llm",
      "profession": "Drainage and flood protection specialist",
      "example_name": "Example Drainage Services Ltd",
      "reason": "The drainage wells and flood pump should be checked before the rain peaks",
      "price_estimate": {
        "min_eur": 300, "max_eur": 1200, "currency": "EUR", "includes_vat": true,
        "basis": "Drainage well inspection, pump check or rental"
      }
    },
    "generated_at": "2026-10-17T10:05:31Z"
  }
}
```

| Kenttä | Kuvaus |
|---|---|
| `alert_id` | hälytyksen tunniste |
| `fingerprint` | `<ryhmä>:<kohde>`; sama tilanne on aktiivisena vain kerran, eskalointi päivittää samaa hälytystä |
| `rule_id` | sääntö, joka tällä hetkellä määrää hälytyksen (ks. [säännöt](#säännöt)) |
| `source_id` | kohde muodossa `house-<id>`, jossa `<id>` on consolidatorin talon id |
| `area` | kaupunki osoitteesta |
| `severity` | `info`, `low`, `medium`, `high`, `critical` |
| `category` | ratkaisijakategoria: `katto`, `kosteus`, `lvi`, `palo`, `automaatio` |
| `status` | `active` tai `resolved` |
| `message` | suomenkielinen kuvaus, valmis näytettäväksi |
| `value`, `details` | mitattu arvo ja säännön laskentatiedot; kuitatussa hälytyksessä `details.resolution_reason` (`condition_cleared` tai `rule_removed`) |
| `revision` | kasvaa, kun vakavuus tai arvo muuttuu |
| `first_seen` / `last_seen` | ensimmäinen ja viimeisin havainto |
| `analysis` | ks. alla |

### analysis

| `analysis.status` | Merkitys |
|---|---|
| `pending` | analyysi tulossa (Qwen ~20–30 s per hälytys); hälytys palaa tähän tilaan myös `escalated`- ja `changed`-tapahtumissa |
| `done` | Qwenin analyysi valmis (`source: "llm"`) |
| `skipped` | agentti pois päältä, pelikirjasuositus (`source: "playbook"`, `reason: "agent_disabled"`) |
| `failed` | Qwen epäonnistui 3 kertaa, pelikirjasuositus (`source: "playbook"`, `reason: "agent_failed: ..."`) |

| Kenttä | Kuvaus |
|---|---|
| `assessment` | arvio tilanteesta juuri tälle talolle (vain `llm`) |
| `likely_cause` | todennäköisin vahinkomekanismi (vain `llm`) |
| `recommendation` | suositeltu toimenpide; pelikirjassa ensimmäinen vakiotoimenpide |
| `urgency` | `immediate`, `today`, `this_week`, `monitor` (pelikirjassa `immediate` kriittisille, muuten `null`) |
| `confidence` | `low`, `medium`, `high` (vain `llm`) |
| `playbook_actions` | säännön vakiotoimenpiteet |
| `suggested_resolvers` | ehdotetut yritykset yhteystietoineen; malli voi ehdottaa vain kannassa olevia |
| `suggested_expert` | asiantuntijaehdotus hinta-arvioineen, ks. alla |

`analysis`-kentän tekstikentät voivat olla `null`, joten tarkista ne ennen näyttämistä.
Agentin tekstit (`assessment`, `likely_cause`, `recommendation`) ja pelikirjojen suositukset ovat englanniksi.

#### suggested_expert

Ehdotus siitä, millainen asiantuntija työn tekisi, ja arvio sen hinnasta. **Toistaiseksi ehdotus on
esimerkki** (`registered: false`): yrityksen nimi on keksitty, eikä yhteystietoja ole. Myöhemmin
tilalle tulee kumppanitietokannasta haettu rekisteröity yritys (`registered: true`).

| Kenttä | Kuvaus |
|---|---|
| `registered` | `false` = kielimallin tai pelikirjan esimerkki, ei oikea kumppani |
| `source` | `llm` (Qwenin arvio tälle kohteelle) tai `playbook` (säännön vakioarvio, kun Qwen ei ole käytössä tai ei antanut ehdotusta) |
| `profession` | asiantuntijan ammatti, esim. `Roofer`, `Plumber` |
| `example_name` | keksitty esimerkkinimi, esim. `Example Roofing Ltd` |
| `reason` | miksi juuri tämä asiantuntija |
| `price_estimate.min_eur` / `max_eur` | hinta-arvion vaihteluväli euroina, sis. ALV |
| `price_estimate.basis` | mitä arvio kattaa, esim. `Roof inspection, 2–4 h` |

Hinta on karkea arvio suomalaisesta hintatasosta, ei tarjous. Kenttä voi olla `null`, jos säännöllä
ei ole pelikirjaa.

## Säännöt

Samaan ryhmään kuuluvat säännöt tuottavat yhden hälytyksen, jonka vakavuus nousee tilanteen pahentuessa.

| Ryhmä | `rule_id` | Ehto | Vakavuus |
|---|---|---|---|
| rain | `heavy_rain` | sade tänään ≥ 10 mm | high |
| | `extreme_rain` | sade tänään ≥ 25 mm | critical |
| wind | `storm_forecast` | tuuli lähipäivinä ≥ 15 m/s | medium |
| | `storm_wind` | tuuli tänään ≥ 15 m/s | high |
| | `severe_storm` | tuuli tänään ≥ 21 m/s | critical |
| frost | `frost_forecast` | pakkasta lähipäivinä ≤ 0 °C | medium |
| | `hard_frost` | tänään ≤ −15 °C | high |
| flood | `flood_warning` | consolidatorin tulvavaroitus | high |
| | `flood_severe` | consolidatorin vakava tulvavaroitus | critical |
| forest_fire | `forest_fire_warning` | consolidatorin maastopalovaroitus | high |
| | `forest_fire_severe` | consolidatorin vakava maastopalovaroitus | critical |
| – | `rain_accumulation` | sade lähipäivinä yhteensä ≥ 30 mm | medium |
| – | `no_data` | kohteesta ei dataa 10 minuuttiin | high |

Kriittiset säännöt ja consolidatorin varoitukset arvioidaan minuutin välein, muut tasatunnein.
Raja-arvot ovat tiedostossa `config/rules.yaml`.

## Testaus

```bash
uv run pytest -q                       # automaattiset testit
uv run python scripts/demo.py          # 4 tunnin myrskysimulaatio ilman palvelimia
```

Koko ketju palvelimilla:

```bash
# käynnistä Logical Unit asetuksella ENABLE_ADMIN_ENDPOINTS=true
curl localhost:8008/app/simulate/storm         # myrsky consolidatoriin
# odota 3–4 min
curl -X POST localhost:8001/admin/evaluate     # tuntisäännöt heti
curl localhost:8001/alerts
```

## Asetukset

Ympäristömuuttujat; Qwen-asetukset kannattaa laittaa tiedostoon `logical-unit/.env` (ei mene Gitiin).

| Muuttuja | Oletus | Kuvaus |
|---|---|---|
| `CONSOLIDATOR_URL` | `http://localhost:8008` | Data Consolidatorin osoite |
| `POLL_SECONDS` | 60 | datan hakuväli |
| `NOTIFY_ENABLED` | true | push-ilmoitukset consolidatorin `/app/notify`-rajapintaan |
| `NOTIFY_EVENTS` | `created,escalated,resolved,analyzed` | tapahtumat, joista ilmoitetaan (pilkuilla eroteltu) |
| `NOTIFY_SECONDS` | 5 | ilmoitusjonon tarkistusväli |
| `NOTIFY_MAX_ATTEMPTS` | 5 | yritykset ennen kuin ilmoitus ohitetaan |
| `AGENT_ENABLED` | false | Qwen-agentti päälle |
| `LLM_BASE_URL` | `http://localhost:11434/v1` | OpenAI-yhteensopiva osoite |
| `LLM_MODEL` | `qwen3:8b` | malli |
| `LLM_API_KEY` | `ollama` | API-avain |
| `ENABLE_ADMIN_ENDPOINTS` | false | `POST /admin/evaluate` |
| `DB_PATH` | `data/alerts.db` | SQLite-kanta |
| `RENOTIFY_HOURS` | 6 | muuttumattoman hälytyksen muistutusväli |
| `CHANGE_THRESHOLD_PCT` | 10 | arvon muutos, joka tuottaa `changed`-tapahtuman |

Ratkaisijat ja pelikirjat (`config/resolvers.yaml`) ladataan vain tyhjään kantaan. Muutosten
jälkeen poista `data/alerts.db` tai aja `uv run python -m app.seed config/resolvers.yaml`.
Tiedoston yritykset ovat keksittyjä esimerkkejä.
