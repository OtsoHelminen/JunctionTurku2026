-- SQLite schema for the data consolidator.
-- Houses are the estates we track; alerts are raised from weather events
-- that threaten a house (heavy rain, storm wind).

PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS houses (
    id                INTEGER PRIMARY KEY AUTOINCREMENT,
    address           TEXT    NOT NULL UNIQUE,
    latitude          REAL    NOT NULL,
    longitude         REAL    NOT NULL,
    construction_year INTEGER,
    house_type        TEXT,
    floor_area_m2     REAL,
    number_of_floors  INTEGER,
    condition         TEXT,
    created_at        TEXT    NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS alerts (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    house_id    INTEGER NOT NULL REFERENCES houses(id) ON DELETE CASCADE,
    alert_type  TEXT    NOT NULL,          -- e.g. 'heavy_rain', 'storm_wind'
    severity    TEXT    NOT NULL,          -- 'low' | 'medium' | 'high'
    message     TEXT    NOT NULL,
    forecast_date TEXT  NOT NULL,          -- YYYY-MM-DD the alert applies to
    created_at  TEXT    NOT NULL DEFAULT (datetime('now'))
);

CREATE INDEX IF NOT EXISTS idx_alerts_house ON alerts(house_id);
CREATE INDEX IF NOT EXISTS idx_alerts_date  ON alerts(forecast_date);
