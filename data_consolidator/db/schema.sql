-- SQLite schema for the data consolidator.
-- Houses are the estates we track; each house is linked to a user (user_id)
-- and has a location used to match nearby weather events.

PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS houses (
    id                INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id           TEXT    NOT NULL,
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

CREATE INDEX IF NOT EXISTS idx_houses_user ON houses(user_id);
