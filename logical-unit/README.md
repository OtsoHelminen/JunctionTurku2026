# Logical Unit

Arkkitehtuurin "Generate"-osa: ottaa vastaan Data Consolidatorin JSONin minuutin välein,
tunnistaa hälytykset sääntöjen perusteella, tallentaa ne SQLiteen ja rikastaa ne
Qwen-agentin arviolla ja ratkaisijaehdotuksella. App lukee hälytykset kannasta.

```
Data Consolidator ──POST /input (JSON, 1/min)──▶ Logical Unit ──▶ SQLite ◀── App
                                                   │
                         minuuttiajo:  raakadata > 60 min → tuntikooste, poisto
                                       immediate-säännöt (kriittiset heti)
                         tuntiajo:     kaikki säännöt → luo / päivitä / kuittaa
                         taustatyö:    Qwen-agentti analysoi uudet hälytykset
```

## Rakenne

```
logical-unit/
├── app/
│   ├── main.py            käynnistys: kanta, säännöt, ajastin, agentti
│   ├── api.py             HTTP-rajapinta
│   ├── models.py          syöte-JSONin malli ja validointi
│   ├── schema.sql         SQLite-taulut
│   ├── db.py              yhteydet ja transaktiot (WAL-tila)
│   ├── repository.py      kaikki SQL-kyselyt
│   ├── jobs.py            minuutti- ja tuntiajot
│   ├── lifecycle.py       hälytysten elinkaari: luonti, eskalointi, muistutus, kuittaus
│   ├── serializers.py     hälytys-JSONin muoto
│   ├── seed.py            ratkaisijoiden lataus YAMLista
│   ├── rules/engine.py    sääntömoottori (deterministinen)
│   └── agent/
│       ├── llm.py         OpenAI-yhteensopiva asiakas (Ollama, vLLM, hostattu Qwen)
│       ├── analyst.py     agentti, työkalut, vastauksen validointi, varasuositus
│       └── worker.py      taustatyö, joka analysoi odottavat hälytykset
├── config/
│   ├── rules.yaml         hälytyssäännöt  ← tätä muokataan eniten
│   └── resolvers.yaml     ratkaisijat ja pelikirjat (esimerkkidataa)
├── scripts/
│   ├── demo.py            4 tunnin simulaatio sekunneissa
│   └── send_sample.py     lähettää dataa käynnissä olevalle palvelulle
├── tests/                 pytest
├── Dockerfile
└── docker-compose.yml     Logical Unit + Ollama (Qwen)
```

## Käynnistys

**Paikallisesti ilman Dockeria** (agentti pois päältä, käytetään pelikirjasuosituksia):

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements-dev.txt
pytest                                   # testit
python scripts/demo.py                   # simulaatio: näet hälytykset ja JSONin
uvicorn app.main:app --reload            # palvelu portissa 8000
python scripts/send_sample.py --scenario leak --interval 5   # toisessa terminaalissa
```

**Dockerilla Qwenin kanssa:**

```bash
docker compose up -d --build
docker compose exec ollama ollama pull qwen3:8b
curl localhost:8000/health
```

## Säännöt: miten hälytys syntyy

Hälytyksen syntymisen päättää aina `config/rules.yaml`, ei kielimalli. Säännöt ovat
deklaratiivisia, joten raja-arvoja voi muuttaa ilman koodimuutoksia (käynnistä palvelu uudelleen).

| Tyyppi | Kysymys | Esimerkki |
|---|---|---|
| `threshold` | Ylittääkö/alittaako arvo rajan? | paineen keskiarvo 15 min < 2 bar |
| `change` | Muuttuiko arvo paljon ikkunan aikana? | paine laski yli 25 % tunnissa |
| `sustained` | Onko ehto ollut voimassa koko ajan? | virtausta > 0,5 l/min koko tunnin |
| `flatline` | Onko arvo jumissa (anturivika)? | paine täsmälleen sama tunnin |
| `missing_data` | Lakkasiko data tulemasta? | ei dataa 10 minuuttiin |

Jokainen sääntö palauttaa yhden kolmesta tuloksesta: **täyttyy**, **ei täyty** tai
**ei tiedetä** (liian vähän dataa). Kolmas tila estää sen, että datan katkeaminen
kuittaisi hälytykset virheellisesti kunnossa-tilaan.

**Ryhmät ja eskalointi.** Samaan `group`-ryhmään kuuluvat säännöt tuottavat yhden hälytyksen,
jossa vakavin voittaa. Esimerkiksi `pressure_low` (medium) ja `pressure_critical` (critical)
ovat samaa ryhmää: kun paine putoaa kriittiseksi, olemassa oleva hälytys eskaloituu.

**Immediate.** `immediate: true` -säännöt arvioidaan joka minuutti, muut kerran tunnissa.

### Milloin hälytys lähtee

| Tilanne | Tapahtuma | Agentti ajetaan |
|---|---|---|
| Uusi tilanne | `created` | kyllä |
| Vakavuus nousee | `escalated` (heti, myös minuuttiajossa) | kyllä |
| Vakavuus laskee tai arvo muuttuu ≥ `CHANGE_THRESHOLD_PCT` | `changed` | kyllä |
| Ennallaan, `RENOTIFY_HOURS` kulunut | `reminder` | ei |
| Ennallaan | ei mitään | ei |
| Ehto ei enää täyty | `resolved` | ei |

Näin hälytyksiä tulee tunnin välein vain, jos on jotain uutta. Muuttumaton tilanne
muistutetaan harvemmin (oletus 6 h).

### Uuden säännön lisääminen

1. Lisää sääntö `config/rules.yaml`-tiedostoon. Virheellinen sääntö (tuntematon parametri,
   kirjoitusvirhe, puuttuva raja-arvo) pysäyttää käynnistyksen selkeällä virheilmoituksella.
2. Lisää pelikirja `config/resolvers.yaml`-tiedostoon samalla `id`:llä.
3. Kirjoita testi `tests/test_rules.py`-tiedostoon.

Jos tarvitset säännön, jota mikään tyyppi ei kata (esim. kahden mittarin yhdistelmä),
lisää uusi arvioijafunktio `app/rules/engine.py`:n `EVALUATORS`-sanakirjaan.

## Qwen-agentti

Agentti käynnistyy vasta, kun hälytys on jo tallennettu (`analysis.status: pending`).
Se saa käyttöönsä neljä lukevaa työkalua, jotka on rajattu hälytyksen omaan kohteeseen:

- `get_recent_readings` – minuuttilukemat (≤ 60 min)
- `get_hourly_history` – tuntikoosteet (≤ 7 vrk)
- `find_resolvers` – ratkaisijat kategorian ja alueen mukaan (ilman yhteystietoja)
- `get_playbook` – säännön vakiotoimenpiteet

Vastaus validoidaan skeemaa vasten. Ratkaisijaehdotuksista hyväksytään vain ne, jotka
`find_resolvers` oikeasti palautti, ja yhteystiedot liitetään kannasta. Jos malli on pois
päältä tai epäonnistuu kolmesti, hälytys saa pelikirjaan perustuvan suosituksen
(`analysis.source: "playbook"`), joten App saa aina toimenpide-ehdotuksen.

Mallin vaihto: `LLM_MODEL`, `LLM_BASE_URL` ja `LLM_API_KEY`. Mikä tahansa
OpenAI-yhteensopiva rajapinta käy (Ollama, vLLM tai hostattu Qwen-palvelu).
Ilman näytönohjainta 8B-malli toimii, mutta yksi analyysi voi kestää minuutteja.

## Rajapinnat

| Metodi | Polku | Kuvaus |
|---|---|---|
| POST | `/input` | yksi JSON-viesti tai lista (≤ 1000) |
| GET | `/health` | terveystarkistus |
| GET | `/alerts?status=active&updated_after=…` | hälytysten nykytila |
| GET | `/alerts/{id}` | yksittäinen hälytys |
| GET | `/events?after_id=N` | hälytysvirta; App tallentaa `last_id`:n ja kysyy siitä eteenpäin |
| POST | `/admin/evaluate` | täysi arviointi heti (vain kun `ENABLE_ADMIN_ENDPOINTS=true`) |

Syöte (`examples/input.json`):

```json
{
  "source_id": "site-42",
  "timestamp": "2026-10-17T08:00:00Z",
  "area": "Helsinki",
  "metrics": { "water_pressure_bar": 3.05, "flow_l_min": 0.0, "temperature_c": 19.4 }
}
```

Hälytyksen JSON-muodon näet ajamalla `python scripts/demo.py`.

## Miten App lukee hälytykset

SQLite on tiedosto, ei verkkopalvelin. Vaihtoehtoja on kaksi:

1. **Sama kone:** App avaa saman tiedoston vain luku -tilassa (Dockerissa sama `alert-data`-volyymi
   `:ro`-liitoksella). WAL-tila sallii lukemisen kirjoituksen aikana.
2. **Eri kone:** App käyttää `/alerts`- ja `/events`-rajapintoja.

Taulut Appin näkökulmasta: `alerts` (nykytila), `alert_events` (virta), `resolvers`.

## Asetukset (ympäristömuuttujat)

| Muuttuja | Oletus | Kuvaus |
|---|---|---|
| `DB_PATH` | `data/alerts.db` | SQLite-tiedosto |
| `RULES_PATH` | `config/rules.yaml` | säännöt |
| `SEED_PATH` | `config/resolvers.yaml` | ratkaisijat (ladataan, jos taulu on tyhjä) |
| `RETENTION_MINUTES` | 60 | raakadatan säilytys |
| `SUMMARY_RETENTION_DAYS` | 30 | tuntikoosteiden säilytys |
| `EVALUATION_INTERVAL_MINUTES` | 60 | täyden arvioinnin väli |
| `RENOTIFY_HOURS` | 6 | muuttumattoman hälytyksen muistutusväli |
| `CHANGE_THRESHOLD_PCT` | 10 | arvon muutos, joka lasketaan uudeksi tiedoksi |
| `AGENT_ENABLED` | false | Qwen-agentti päälle |
| `LLM_BASE_URL` | `http://localhost:11434/v1` | mallin osoite |
| `LLM_MODEL` | `qwen3:8b` | malli |
| `ENABLE_ADMIN_ENDPOINTS` | false | `/admin/evaluate` |

Ratkaisijoiden päivitys ajossa olevaan kantaan: `python -m app.seed config/resolvers.yaml`.

## Huomioita

- Aja yhdellä prosessilla (ei `--workers`), muuten ajastin käynnistyy useaan kertaan.
- Syötteen aikaleima ratkaisee, mihin minuuttiin lukema kuuluu. Säilytysikkunaa vanhemmat
  lukemat ohitetaan, ja yli 5 min tulevaisuudessa olevat hylätään.
- `config/resolvers.yaml` sisältää keksittyjä yrityksiä. Korvaa ne oikeilla kumppaneilla.
- Mittarinimet ja raja-arvot ovat esimerkkejä. Sovi oikeat arvot asiantuntijan kanssa ja
  muuta `app/models.py` vastaamaan Data Consolidatorin lopullista JSON-muotoa.
