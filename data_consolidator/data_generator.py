

"""Zonal weather simulation and house-local event streams (WGS84 input/output).

Requires pyproj. Zones are 100,000 m squares in Finland's EPSG:3067 grid.
Regional events have estate=None; house-local events contain the saved house row.
"""
from __future__ import annotations

import copy
import math
import random
import threading
from collections import deque
from datetime import date, datetime, timedelta, timezone
from typing import Any

from pyproj import Geod, Transformer

HISTORY_SIZE = 60
FORECAST_DAYS = 3
ZONE_SIZE_M = 100_000
HOUSE_RADIUS_KM = 25.0
# Configurable rectangular simulation extent, not a Finnish land-border mask.
SOUTHERN_FINLAND_BOUNDS = (59.7, 61.8, 21.0, 29.5)
WIND_DIRECTIONS = ['N', 'NE', 'E', 'SE', 'S', 'SW', 'W', 'NW']
TEMP_BOUNDS = (-30.0, 35.0)
TEMP_STEP = 1.0
SPREAD_BOUNDS = (2.0, 15.0)
SPREAD_STEP = 0.5
RAIN_BOUNDS = (0.0, 50.0)
RAIN_STEP = 1.5
WIND_BOUNDS = (0.0, 25.0)
WIND_STEP = 1.0
ESTATE = {
    'construction_year': 1978, 'renovation_years': [1998, 2015],
    'house_type': 'detached', 'shape': 'rectangular', 'floor_area_m2': 142.5,
    'number_of_floors': 2, 'condition': 'good',
    'address': 'Koivukuja 12, 00930 Helsinki, Finland',
}
_TO_GRID = Transformer.from_crs('EPSG:4326', 'EPSG:3067', always_xy=True)
_TO_WGS = Transformer.from_crs('EPSG:3067', 'EPSG:4326', always_xy=True)
_GEOD = Geod(ellps='WGS84')


def _clamp(value: float, low: float, high: float) -> float:
    return max(low, min(high, value))


def _conditions(rain_mm: float, max_c: float) -> str:
    if rain_mm >= 10:
        return 'snow' if max_c <= 0 else 'heavy rain'
    if rain_mm >= 1:
        return 'snow showers' if max_c <= 0 else 'rain showers'
    if rain_mm > 0:
        return 'cloudy'
    return 'partly cloudy' if max_c < 15 else 'sunny'


class DataGenerator:
    def __init__(self, seed: int | None = None, start_date: date | None = None,
                 bounds: tuple[float, float, float, float] = SOUTHERN_FINLAND_BOUNDS) -> None:
        self._rng = random.Random(seed)
        self._house_seed = self._rng.getrandbits(128)
        self._house_rng: dict[int, random.Random] = {}
        self._start_date = start_date
        self.bounds = bounds
        south, north, west, east = bounds
        if not (-90 < south < north < 90 and -180 < west < east < 180):
            raise ValueError('Invalid simulation bounds')
        self._lock = threading.RLock()
        self._storm_remaining = 0
        self._timestamp: datetime | None = None
        self.history: deque[dict[str, Any]] = deque(maxlen=HISTORY_SIZE)
        self._frames: deque[dict[str, Any]] = deque(maxlen=HISTORY_SIZE)
        self._houses: dict[int, dict[str, Any]] = {}
        self._house_history: dict[int, deque[dict[str, Any]]] = {}
        self._zones: dict[str, dict[str, Any]] = {}
        # Densify the rectangle edges to include projection extrema.
        points = []
        for i in range(101):
            t = i / 100
            points.extend([(west + (east-west)*t, south), (west + (east-west)*t, north),
                           (west, south + (north-south)*t), (east, south + (north-south)*t)])
        coords = [_TO_GRID.transform(lon, lat) for lon, lat in points]
        xmin, xmax = min(x for x, _ in coords), max(x for x, _ in coords)
        ymin, ymax = min(y for _, y in coords), max(y for _, y in coords)
        for col in range(math.floor(xmin / ZONE_SIZE_M), math.floor(xmax / ZONE_SIZE_M) + 1):
            for row in range(math.floor(ymin / ZONE_SIZE_M), math.floor(ymax / ZONE_SIZE_M) + 1):
                zone_id = f'{col}:{row}'
                self._zones[zone_id] = {
                    'id': zone_id, 'crs': 'EPSG:3067', 'size_km': 100,
                    'bounds_m': {'min_x': col * ZONE_SIZE_M, 'min_y': row * ZONE_SIZE_M,
                                 'max_x': (col+1) * ZONE_SIZE_M, 'max_y': (row+1) * ZONE_SIZE_M},
                    'days': [{'min_c': 8.0+i+self._rng.uniform(-2, 2), 'spread': 6.0,
                              'rain': 0.0, 'wind': 4.0, 'dir': 4} for i in range(FORECAST_DAYS)],
                }

    @property
    def estate(self) -> dict[str, Any]:
        return copy.deepcopy(ESTATE)

    def contains(self, latitude: float, longitude: float) -> bool:
        south, north, west, east = self.bounds
        return south <= latitude <= north and west <= longitude <= east

    def validate_house(self, latitude: float, longitude: float) -> None:
        if not self.contains(latitude, longitude):
            raise ValueError(
                f'House coordinates must be inside simulation bounds {self.bounds}')

    def register_house(self, house: dict[str, Any]) -> None:
        """Register a DB row and backfill local history without advancing weather."""
        self.validate_house(house['latitude'], house['longitude'])
        house_id = int(house['id'])
        with self._lock:
            if self._houses.get(house_id) == house:
                return
            self._houses[house_id] = copy.deepcopy(house)
            self._house_rng[house_id] = random.Random(
                self._house_seed + house_id)
            history: deque[dict[str, Any]] = deque(maxlen=HISTORY_SIZE)
            for frame in self._frames:
                history.append(self._house_event(house, frame))
            self._house_history[house_id] = history

    def force_storm(self, events: int = 30) -> None:
        """Storm lasts this many simulation ticks, independent of house count."""
        if isinstance(events, bool) or not isinstance(events, int) or events < 0:
            raise ValueError('events must be a non-negative integer')
        with self._lock:
            self._storm_remaining = events

    def _step(self, days: list[dict[str, Any]], storm: bool) -> None:
        r = self._rng
        for d in days:
            d['min_c'] = _clamp(
                d['min_c'] + r.uniform(-TEMP_STEP, TEMP_STEP), *TEMP_BOUNDS)
            d['spread'] = _clamp(
                d['spread'] + r.uniform(-SPREAD_STEP, SPREAD_STEP), *SPREAD_BOUNDS)
            if storm:
                d['rain'] = _clamp(
                    max(10.0, d['rain'] + r.uniform(3, 8)), *RAIN_BOUNDS)
                d['wind'] = _clamp(
                    max(17.0, d['wind'] + r.uniform(2, 5)), *WIND_BOUNDS)
            else:
                # Bounded, mean-reverting walks avoid remaining at storm maxima.
                d['rain'] = _clamp(d['rain'] + _clamp((2-d['rain'])*0.1 + r.uniform(-1, 1),
                                                      -RAIN_STEP, RAIN_STEP), *RAIN_BOUNDS)
                d['wind'] = _clamp(d['wind'] + _clamp((4-d['wind'])*0.1 + r.uniform(-0.7, 0.7),
                                                      -WIND_STEP, WIND_STEP), *WIND_BOUNDS)
            d['dir'] = (d['dir'] + r.choice([-1, 0, 0, 0, 1])
                        ) % len(WIND_DIRECTIONS)

    def _weather(self, days: list[dict[str, Any]], timestamp: datetime) -> dict[str, Any]:
        forecast = []
        base_date = self._start_date or timestamp.date()
        for i, d in enumerate(days):
            low = round(d['min_c'], 1)
            high = round(min(d['min_c']+d['spread'], TEMP_BOUNDS[1]), 1)
            rain = round(d['rain'], 1)
            forecast.append({'date': (base_date+timedelta(days=i)).isoformat(),
                             'temperature': {'min_c': low, 'max_c': max(low, high)},
                             'rainfall_mm': rain,
                             'wind': {'speed_m_s': round(d['wind'], 1), 'direction': WIND_DIRECTIONS[d['dir']]},
                             'conditions': _conditions(rain, high)})
        return {'forecast': forecast}

    def _zone_id(self, location: dict[str, float]) -> str:
        x, y = _TO_GRID.transform(location['longitude'], location['latitude'])
        return f'{math.floor(x/ZONE_SIZE_M)}:{math.floor(y/ZONE_SIZE_M)}'

    def _zone_metadata(self, zone_id: str) -> dict[str, Any]:
        return copy.deepcopy({k: v for k, v in self._zones[zone_id].items() if k != 'days'})

    def _house_event(self, house: dict[str, Any], frame: dict[str, Any]) -> dict[str, Any]:
        # Uniform disk by area, measured geodesically; clip at simulation boundaries.
        rng = self._house_rng[int(house['id'])]
        location = None
        for _ in range(1000):
            radius_m = math.sqrt(rng.random()) * HOUSE_RADIUS_KM * 1000
            lon, lat, _ = _GEOD.fwd(
                house['longitude'], house['latitude'], rng.uniform(0, 360), radius_m)
            candidate = {'latitude': lat, 'longitude': lon}
            if self.contains(lat, lon) and self._zone_id(candidate) in frame['weather']:
                location = candidate
                break
        if location is None:
            location = {'latitude': house['latitude'],
                        'longitude': house['longitude']}
        zone_id = self._zone_id(location)
        return {'timestamp': frame['timestamp'], 'location': location,
                'zone': self._zone_metadata(zone_id), 'storm': frame['storm'],
                'weather': copy.deepcopy(frame['weather'][zone_id]), 'estate': copy.deepcopy(house)}

    def generate_events(self) -> list[dict[str, Any]]:
        """Advance every zone once; produce regional and per-house events."""
        with self._lock:
            self._timestamp = self._timestamp + \
                timedelta(minutes=1) if self._timestamp else datetime.now(
                    timezone.utc)
            storm = self._storm_remaining > 0
            if storm:
                self._storm_remaining -= 1
            weather = {}
            events = []
            for zone_id, zone in self._zones.items():
                self._step(zone['days'], storm)
                weather[zone_id] = self._weather(zone['days'], self._timestamp)
                b = zone['bounds_m']
                # Boundary zones are clipped to the configured geographic extent.
                for _ in range(500):
                    lon, lat = _TO_WGS.transform(self._rng.uniform(b['min_x'], b['max_x']),
                                                 self._rng.uniform(b['min_y'], b['max_y']))
                    if self.contains(lat, lon):
                        event = {'timestamp': self._timestamp, 'location': {'latitude': lat, 'longitude': lon},
                                 'zone': self._zone_metadata(zone_id), 'storm': storm,
                                 'weather': copy.deepcopy(weather[zone_id]), 'estate': None}
                        events.append(event)
                        self.history.append(event)
                        break
            frame = {'timestamp': self._timestamp,
                     'storm': storm, 'weather': weather}
            self._frames.append(frame)
            for house_id, house in self._houses.items():
                self._house_history[house_id].append(
                    self._house_event(house, frame))
            return copy.deepcopy(events)

    def generate_event(self) -> dict[str, Any]:
        """Compatibility wrapper: advances a tick and returns one regional event."""
        events = self.generate_events()
        if not events:
            raise RuntimeError(
                'Simulation extent contains no generated locations')
        return events[0]

    def initialize_history(self, count: int = HISTORY_SIZE) -> None:
        if count < 0:
            raise ValueError('count must be non-negative')
        with self._lock:
            if self._timestamp is None and count:
                self._timestamp = datetime.now(
                    timezone.utc) - timedelta(minutes=count)
            for _ in range(count):
                self.generate_events()

    def latest(self, count: int = HISTORY_SIZE) -> list[dict[str, Any]]:
        with self._lock:
            return copy.deepcopy(list(reversed(self.history))[:max(0, count)])

    def latest_for_house(self, house_id: int, count: int = HISTORY_SIZE) -> list[dict[str, Any]]:
        with self._lock:
            if house_id not in self._house_history:
                raise KeyError(house_id)
            return copy.deepcopy(list(reversed(self._house_history[house_id]))[:max(0, count)])
