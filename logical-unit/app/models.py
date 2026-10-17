"""Data Consolidatorin JSONin malli (ks. data_consolidator/data_template).

Logical Unit hakee kohteen datan osoitteesta GET /app/data_events/{house_id}. Sama vastaus
kelpaa sellaisenaan myös POST /input -rajapintaan:

{
  "house": {"id": 1, "address": "Koivukuja 12, 00930 Helsinki, Finland",
            "latitude": 60.2, "longitude": 24.94, "construction_year": 1978, ...},
  "radius_km": 25.0,
  "data_events": [                      # uusin ensin, yksi minuutissa
    {"timestamp": "2026-10-17T10:59:36.844925Z",
     "location": {"latitude": 60.11, "longitude": 24.70},
     "weather": {"forecast": [
        {"date": "2026-10-17", "temperature": {"min_c": 7.9, "max_c": 13.8},
         "rainfall_mm": 0.4, "wind": {"speed_m_s": 4.2, "direction": "S"}, "conditions": "cloudy"},
        ...]},
     "extremes": [{"type": "flood", "severity": "warning", "description": "...", ...}],
     "estate": {"id": 1, "construction_year": 1978, ...}}
  ]
}

Muut kentät (zone, storm jne.) ohitetaan.
"""

from __future__ import annotations

import math
from datetime import datetime, timezone
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator


class _Model(BaseModel):
    model_config = ConfigDict(extra="ignore")


def _finite(value: float) -> float:
    if not math.isfinite(value):
        raise ValueError("value is not a finite number")
    return value


class Temperature(_Model):
    min_c: float
    max_c: float

    _check = field_validator("min_c", "max_c")(_finite)


class Wind(_Model):
    speed_m_s: float = Field(ge=0)
    direction: str | None = None

    _check = field_validator("speed_m_s")(_finite)


class ForecastDay(_Model):
    date: str
    temperature: Temperature
    rainfall_mm: float = Field(ge=0)
    wind: Wind
    conditions: str | None = None

    _check = field_validator("rainfall_mm")(_finite)


class Weather(_Model):
    forecast: list[ForecastDay] = Field(min_length=1)


class Extreme(_Model):
    """Extreme event computed by the consolidator for a zone, e.g. flood or forest_fire."""

    type: str
    severity: str                       # warning | severe
    description: str | None = None


class DataEvent(_Model):
    timestamp: datetime | None = None
    location: dict[str, float] | None = None
    weather: Weather
    extremes: list[Extreme] = Field(default_factory=list)
    estate: dict[str, Any] | None = None

    def epoch(self, now: int) -> int:
        """Aikaleima unix-sekunteina. Puuttuva = hakuhetki, ilman aikavyöhykettä = UTC."""
        if self.timestamp is None:
            return now
        ts = self.timestamp
        if ts.tzinfo is None:
            ts = ts.replace(tzinfo=timezone.utc)
        return int(ts.timestamp())


class House(_Model):
    id: int
    address: str = Field(min_length=1, max_length=300)
    latitude: float | None = None
    longitude: float | None = None
    construction_year: int | None = None
    house_type: str | None = None
    floor_area_m2: float | None = None
    number_of_floors: int | None = None
    condition: str | None = None


class HouseEvents(_Model):
    """Response of the Data Consolidator GET /app/data_events/{house_id} call."""

    house: House
    data_events: list[DataEvent] = Field(default_factory=list)
