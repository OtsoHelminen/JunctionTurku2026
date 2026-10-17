"""Data Consolidatorin JSONin malli (ks. data_consolidator/data_template).

Logical Unit hakee kohteen datan osoitteesta GET /app/data_events/{house_id}. Sama vastaus
kelpaa sellaisenaan myös POST /input -rajapintaan:

{
  "house": {"id": 1, "address": "Koivukuja 12, 00930 Helsinki, Finland",
            "latitude": 60.2, "longitude": 24.94, "construction_year": 1978, ...},
  "radius_km": 25.0,
  "data_events": [                      # uusin ensin
    {"location": {"latitude": 60.21, "longitude": 24.9},
     "weather": {"forecast": [
        {"date": "2026-10-17", "temperature": {"min_c": 7.9, "max_c": 13.8},
         "rainfall_mm": 0.4, "wind": {"speed_m_s": 4.2, "direction": "S"}, "conditions": "cloudy"},
        ...]},
     "estate": {"construction_year": 1978, "renovation_years": [1998, 2015], ...}}
  ]
}
"""

from __future__ import annotations

import math
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator


class _Model(BaseModel):
    model_config = ConfigDict(extra="ignore")


def _finite(value: float) -> float:
    if not math.isfinite(value):
        raise ValueError("arvo ei ole äärellinen luku")
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


class DataEvent(_Model):
    location: dict[str, float] | None = None
    weather: Weather
    estate: dict[str, Any] | None = None


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
    """Vastaus Data Consolidatorin GET /app/data_events/{house_id} -kutsuun."""

    house: House
    data_events: list[DataEvent] = Field(default_factory=list)
