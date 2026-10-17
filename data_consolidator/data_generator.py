"""In-memory generator for weather + estate data events matching data_template.json."""

from __future__ import annotations

import copy
import random
from collections import deque
from datetime import date, timedelta
from typing import Any

HISTORY_SIZE = 60
FORECAST_DAYS = 3

WIND_DIRECTIONS = ["N", "NE", "E", "SE", "S", "SW", "W", "NW"]

# Bounds and maximum per-event step sizes for the random walk.
TEMP_BOUNDS = (-30.0, 35.0)
TEMP_STEP = 1.0
SPREAD_BOUNDS = (2.0, 15.0)
SPREAD_STEP = 0.5
RAIN_BOUNDS = (0.0, 50.0)
RAIN_STEP = 1.5
WIND_BOUNDS = (0.0, 25.0)
WIND_STEP = 1.0

ESTATE: dict[str, Any] = {
    "construction_year": 1978,
    "renovation_years": [1998, 2015],
    "house_type": "detached",
    "shape": "rectangular",
    "floor_area_m2": 142.5,
    "number_of_floors": 2,
    "condition": "good",
    "address": "Koivukuja 12, 00930 Helsinki, Finland",
}

# Events are scattered over a 50 km x 50 km area centered on Helsinki.
AREA_CENTER_LAT = 60.20
AREA_CENTER_LON = 24.94
# 25 km in degrees: ~0.225 deg latitude, ~0.45 deg longitude at 60 deg N.
AREA_HALF_LAT = 0.225
AREA_HALF_LON = 0.45


def _clamp(value: float, low: float, high: float) -> float:
    return max(low, min(high, value))


def _conditions(rain_mm: float, max_c: float) -> str:
    if rain_mm >= 10:
        return "snow" if max_c <= 0 else "heavy rain"
    if rain_mm >= 1:
        return "snow showers" if max_c <= 0 else "rain showers"
    if rain_mm > 0:
        return "cloudy"
    return "partly cloudy" if max_c < 15 else "sunny"


class DataGenerator:
    """Produces events whose weather follows a bounded random walk; estate stays constant."""

    def __init__(self, seed: int | None = None, start_date: date | None = None) -> None:
        self._rng = random.Random(seed)
        self._start_date = start_date or date.today()
        self._estate = copy.deepcopy(ESTATE)
        self._days: list[dict[str, float]] = [
            {"min_c": 8.0 + i, "spread": 6.0, "rain": 0.0, "wind": 4.0, "dir": 4}
            for i in range(FORECAST_DAYS)
        ]
        self.history: deque[dict[str, Any]] = deque(maxlen=HISTORY_SIZE)
        self._storm_remaining = 0

    def force_storm(self, events: int = 30) -> None:
        """Make the next `events` generated events stormy: heavy rain and wind."""
        self._storm_remaining = max(0, events)

    @property
    def estate(self) -> dict[str, Any]:
        return copy.deepcopy(self._estate)

    def _step(self) -> None:
        r = self._rng
        storm = self._storm_remaining > 0
        if storm:
            self._storm_remaining -= 1
        for d in self._days:
            if storm:
                d["rain"] = _clamp(
                    d["rain"] + r.uniform(5.0, 15.0), *RAIN_BOUNDS)
                d["wind"] = _clamp(
                    d["wind"] + r.uniform(8.0, 20.0), *WIND_BOUNDS)
                if r.random() < 0.3:
                    d["min_c"] = _clamp(
                        d["min_c"] - r.uniform(0.0, TEMP_STEP), *TEMP_BOUNDS)
                continue
            d["min_c"] = _clamp(
                d["min_c"] + r.uniform(-TEMP_STEP, TEMP_STEP), *TEMP_BOUNDS)
            d["spread"] = _clamp(
                d["spread"] + r.uniform(-SPREAD_STEP, SPREAD_STEP), *SPREAD_BOUNDS)
            d["rain"] = _clamp(
                d["rain"] + r.uniform(-RAIN_STEP, RAIN_STEP), *RAIN_BOUNDS)
            d["wind"] = _clamp(
                d["wind"] + r.uniform(-WIND_STEP, WIND_STEP), *WIND_BOUNDS)
            d["dir"] = (d["dir"] + r.choice([-1, 0, 0, 0, 1])
                        ) % len(WIND_DIRECTIONS)

    def generate_event(self) -> dict[str, Any]:
        """Advance the random walk one step, store and return a new event."""
        self._step()
        forecast = []
        for i, d in enumerate(self._days):
            min_c = round(d["min_c"], 1)
            max_c = round(min(d["min_c"] + d["spread"],
                          TEMP_BOUNDS[1] + SPREAD_BOUNDS[1]), 1)
            rain = round(d["rain"], 1)
            forecast.append(
                {
                    "date": (self._start_date + timedelta(days=i)).isoformat(),
                    "temperature": {"min_c": min_c, "max_c": max(max_c, min_c)},
                    "rainfall_mm": rain,
                    "wind": {
                        "speed_m_s": round(d["wind"], 1),
                        "direction": WIND_DIRECTIONS[int(d["dir"])],
                    },
                    "conditions": _conditions(rain, max_c),
                }
            )
        location = {
            "latitude": round(
                self._rng.uniform(AREA_CENTER_LAT - AREA_HALF_LAT,
                                  AREA_CENTER_LAT + AREA_HALF_LAT), 4
            ),
            "longitude": round(
                self._rng.uniform(AREA_CENTER_LON - AREA_HALF_LON,
                                  AREA_CENTER_LON + AREA_HALF_LON), 4
            ),
        }
        event = {"location": location, "weather": {
            "forecast": forecast}, "estate": self.estate}
        self.history.append(event)
        return event

    def initialize_history(self, count: int = HISTORY_SIZE) -> None:
        for _ in range(count):
            self.generate_event()

    def latest(self, count: int = HISTORY_SIZE) -> list[dict[str, Any]]:
        """Return up to `count` most recent events, newest first."""
        return list(reversed(self.history))[:count]
