-- Logical Unitin SQLite-skeema. Kaikki aikaleimat ovat unix-sekunteja (UTC).

-- Datalähteet (kohteet, source_id = "house-<id>"). last_seen säilyy, vaikka raakadata poistetaan,
-- joten "data puuttuu" -sääntö toimii myös tunnin jälkeen.
CREATE TABLE IF NOT EXISTS sources (
    source_id   TEXT PRIMARY KEY,
    area        TEXT,
    estate      TEXT,                                   -- JSON: kohteen tiedot Data Consolidatorilta
    first_seen  INTEGER NOT NULL,
    last_seen   INTEGER NOT NULL
);

-- Raakalukemat: liukuva ikkuna (oletus 60 min). Yksi rivi per mittari per aikaleima.
CREATE TABLE IF NOT EXISTS readings (
    id         INTEGER PRIMARY KEY,
    source_id  TEXT    NOT NULL,
    metric     TEXT    NOT NULL,
    ts         INTEGER NOT NULL,
    value      REAL    NOT NULL,
    UNIQUE (source_id, metric, ts)
);
CREATE INDEX IF NOT EXISTS idx_readings_ts ON readings (ts);

-- Tuntikooste: lasketaan raakadatasta juuri ennen sen poistoa, joten trenditieto säilyy.
CREATE TABLE IF NOT EXISTS hourly_summary (
    source_id  TEXT    NOT NULL,
    metric     TEXT    NOT NULL,
    hour_ts    INTEGER NOT NULL,
    min_value  REAL    NOT NULL,
    max_value  REAL    NOT NULL,
    sum_value  REAL    NOT NULL,
    count      INTEGER NOT NULL,
    PRIMARY KEY (source_id, metric, hour_ts)
);

-- Hälytysten nykytila. fingerprint = "<sääntöryhmä>:<source_id>".
CREATE TABLE IF NOT EXISTS alerts (
    id                  INTEGER PRIMARY KEY,
    fingerprint         TEXT    NOT NULL,
    rule_id             TEXT    NOT NULL,
    source_id           TEXT    NOT NULL,
    area                TEXT,
    severity            TEXT    NOT NULL,
    category            TEXT,
    status              TEXT    NOT NULL CHECK (status IN ('active', 'resolved')),
    message             TEXT    NOT NULL,
    value               REAL,
    details             TEXT    NOT NULL DEFAULT '{}',   -- JSON
    revision            INTEGER NOT NULL DEFAULT 1,
    first_seen          INTEGER NOT NULL,
    last_seen           INTEGER NOT NULL,
    last_notified       INTEGER NOT NULL,
    resolved_at         INTEGER,
    updated_at          INTEGER NOT NULL,
    analysis_status     TEXT    NOT NULL DEFAULT 'pending'
                        CHECK (analysis_status IN ('pending', 'done', 'failed', 'skipped')),
    analysis            TEXT,                             -- JSON
    analysis_attempts   INTEGER NOT NULL DEFAULT 0,
    analysis_retry_at   INTEGER NOT NULL DEFAULT 0
);
-- Sama tilanne voi olla aktiivisena vain kerran.
CREATE UNIQUE INDEX IF NOT EXISTS idx_alerts_one_active
    ON alerts (fingerprint) WHERE status = 'active';
CREATE INDEX IF NOT EXISTS idx_alerts_updated ON alerts (updated_at);
CREATE INDEX IF NOT EXISTS idx_alerts_pending ON alerts (analysis_status, status);

-- Tapahtumaloki: tämä on se hälytysvirta, jota App lukee (id toimii kursorina).
CREATE TABLE IF NOT EXISTS alert_events (
    id          INTEGER PRIMARY KEY,
    alert_id    INTEGER NOT NULL REFERENCES alerts (id),
    event_type  TEXT    NOT NULL
                CHECK (event_type IN ('created', 'escalated', 'changed', 'reminder', 'resolved', 'analyzed')),
    created_at  INTEGER NOT NULL,
    payload     TEXT    NOT NULL                        -- hälytyksen JSON tapahtumahetkellä
);
CREATE INDEX IF NOT EXISTS idx_events_created ON alert_events (created_at);

-- Ratkaisijat (putkimiehet, LVI, automaatio...). Agentti saa ehdottaa vain näitä.
CREATE TABLE IF NOT EXISTS resolvers (
    id        INTEGER PRIMARY KEY,
    name      TEXT    NOT NULL UNIQUE,
    category  TEXT    NOT NULL,
    areas     TEXT    NOT NULL DEFAULT '["*"]',          -- JSON-lista, "*" = kaikki alueet
    phone     TEXT,
    email     TEXT,
    on_call   INTEGER NOT NULL DEFAULT 0,               -- 1 = päivystää
    priority  INTEGER NOT NULL DEFAULT 100,             -- pienempi = ensisijainen
    notes     TEXT,
    active    INTEGER NOT NULL DEFAULT 1
);
CREATE INDEX IF NOT EXISTS idx_resolvers_category ON resolvers (category, active);

-- Pelikirjat: sääntö -> ratkaisijakategoria + vakiotoimenpiteet.
CREATE TABLE IF NOT EXISTS playbooks (
    rule_id   TEXT PRIMARY KEY,
    category  TEXT NOT NULL,
    actions   TEXT NOT NULL                              -- JSON-lista merkkijonoja
);

-- Push-ilmoitusten lähettäjän kursori: viimeisin alert_events.id, joka on käsitelty.
CREATE TABLE IF NOT EXISTS notifier_state (
    id             INTEGER PRIMARY KEY CHECK (id = 1),
    last_event_id  INTEGER NOT NULL
);
