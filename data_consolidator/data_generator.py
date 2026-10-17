

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
# Covers the cities used by the mobile app's Finnish address suggestions.
FINLAND_BOUNDS = (59.7, 66.7, 21.0, 29.5)
WIND_DIRECTIONS = ['N', 'NE', 'E', 'SE', 'S', 'SW', 'W', 'NW']
TEMP_BOUNDS = (-30.0, 35.0)
TEMP_STEP = 1.0
SPREAD_BOUNDS = (2.0, 15.0)
SPREAD_STEP = 0.5
RAIN_BOUNDS = (0.0, 50.0)
RAIN_STEP = 1.5
WIND_BOUNDS = (0.0, 25.0)
WIND_STEP = 1.0
# Alert thresholds (simulation-tuned, loosely after FMI warning levels).
FLOOD_DAY_MM = 20.0          # one day's rainfall
FLOOD_3DAY_MM = 45.0         # 3-day forecast total
FLOOD_SEVERE_DAY_MM = 35.0
FLOOD_CLEAR_MM = 10.0        # hysteresis: alert stays until rain drops below this
FIRE_MIN_TEMP_C = 22.0       # today's max temperature
FIRE_MAX_RAIN_MM = 0.5       # "dry" day
# consecutive dry ticks needed (soil/vegetation drying)
FIRE_DRY_TICKS = 30
FIRE_SEVERE_TEMP_C = 27.0
FIRE_CLEAR_TEMP_C = 19.0
FROSTBITE_MIN_C = -20.0      # today's min temperature for frostbite risk
FROSTBITE_TICKS = 5          # consecutive severe-cold ticks before the alert
FROSTBITE_SEVERE_C = -25.0
FROSTBITE_CLEAR_C = -15.0    # hysteresis: alert stays until warmer than this
FREEZE_MAX_C = 0.0           # a sub-zero day
FREEZE_TICKS = 15            # consecutive sub-zero ticks before pipes at risk
FREEZE_SEVERE_C = -15.0
# very heavy rain: severe flood level from the first storm tick
STORM_RAIN_MM = 35.0
STORM_WIND_M_S = 21.0        # storm-force wind (FMI 'myrsky' starts at 21 m/s)
RAIN_FRONT_CHANCE = 0.002     # per zone per tick: a slow heavy-rain front arrives
RAIN_FRONT_TARGET_MM = 28.0
DRY_SPELL_CHANCE = 0.003      # per zone per tick: a high-pressure dry spell sets in
# below zero so rain settles at 0 mm         # storms bring very heavy rain -> flood alert
DRY_SPELL_TARGET_MM = -1.0
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
                 bounds: tuple[float, float, float, float] = FINLAND_BOUNDS) -> None:
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
        self._fire_remaining = 0
        self._frost_remaining = 0
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
                    'dry_ticks': 0, 'cold_ticks': 0, 'frost_ticks': 0,
                    'alerts': {}, 'front': 0, 'dry_spell': 0,
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
        """Start a storm over every zone in the configured bounds right now.

        Lasts this many simulation ticks, independent of house count. The first
        storm tick is generated immediately, so the API shows storm weather at
        once instead of waiting for the next background tick (default 60 s).
        """
        if isinstance(events, bool) or not isinstance(events, int) or events < 0:
            raise ValueError('events must be a non-negative integer')
        with self._lock:
            self._storm_remaining = events
            if events:
                self._overwrite_history()
                self._generate_forced(events)

    def force_forest_fire(self, events: int = 60) -> None:
        """Start a heat wave with drought over every zone right now.

        Lasts this many simulation ticks. Temperatures climb above the forest
        fire threshold and rain stops, so after the drying period every zone
        raises a forest fire alert. The first tick is generated immediately.
        """
        if isinstance(events, bool) or not isinstance(events, int) or events < 0:
            raise ValueError('events must be a non-negative integer')
        with self._lock:
            self._fire_remaining = events
            self._frost_remaining = 0  # heat wave and cold snap exclude each other
            if events:
                self._overwrite_history()
                self._generate_forced(events)

    def force_frost(self, events: int = 60) -> None:
        """Start a severe cold snap over every zone right now.

        Lasts this many simulation ticks. Temperatures plunge below -20 °C, so
        frostbite alerts appear within a few ticks and freezing-pipes alerts
        once the cold has persisted. The first tick is generated immediately.
        """
        if isinstance(events, bool) or not isinstance(events, int) or events < 0:
            raise ValueError('events must be a non-negative integer')
        with self._lock:
            self._frost_remaining = events
            self._fire_remaining = 0  # cold snap and heat wave exclude each other
            if events:
                self._overwrite_history()
                self._generate_forced(events)

    def _overwrite_history(self) -> None:
        """Drop all stored events so the forced extreme events replace them.

        Regional history, shared frames and every house's local history are
        cleared; the immediate forced tick and following ticks refill them,
        so /app/data_events soon shows only the simulated extreme weather.
        """
        self.history.clear()
        self._frames.clear()
        for history in self._house_history.values():
            history.clear()

    def _generate_forced(self, events: int) -> None:
        """Generate `events` forced ticks at once so history is instantly full.

        The timeline is shifted back first, so the newest forced event lands
        at the current moment and the batch spans the previous `events`
        minutes. The last tick triggers the mild-baseline reset inside
        generate_events, so normal weather resumes from there.
        """
        if self._timestamp is not None:
            self._timestamp -= timedelta(minutes=events)
        for _ in range(events):
            self.generate_events()

    def _reset_zones_mild(self) -> None:
        """Restart the random walk from a mild baseline after a forced event.

        Without this the walk would decay slowly from storm/frost/heat
        extremes; instead the next normal tick starts near 8 °C, no rain,
        light wind, and all alert counters are cleared.
        """
        for zone in self._zones.values():
            for i, d in enumerate(zone['days']):
                d.update(min_c=8.0 + i + self._rng.uniform(-2, 2), spread=6.0,
                         rain=0.0, wind=4.0, dir=4)
            zone.update(dry_ticks=0, cold_ticks=0, frost_ticks=0,
                        alerts={}, front=0, dry_spell=0)

    def _step(self, zone: dict[str, Any], storm: bool, fire: bool = False,
              frost: bool = False) -> None:
        r = self._rng
        days = zone['days']
        if zone['front'] > 0:
            zone['front'] -= 1
        elif not storm and r.random() < RAIN_FRONT_CHANCE:
            zone['front'] = r.randint(20, 40)
        if zone['dry_spell'] > 0:
            zone['dry_spell'] -= 1
        elif not storm and not zone['front'] and r.random() < DRY_SPELL_CHANCE:
            zone['dry_spell'] = r.randint(60, 120)
        if storm or fire or frost:
            zone['front'] = zone['dry_spell'] = 0
        rain_target = (RAIN_FRONT_TARGET_MM if zone['front']
                       else DRY_SPELL_TARGET_MM if zone['dry_spell'] else 2.0)
        for d in days:
            # Mean-reverting walk toward a mild baseline so forced cold snaps
            # and heat waves decay back to normal weather afterwards.
            d['min_c'] = _clamp(
                d['min_c'] + _clamp((8.0-d['min_c'])*0.05 + r.uniform(-TEMP_STEP, TEMP_STEP),
                                    -TEMP_STEP, TEMP_STEP), *TEMP_BOUNDS)
            d['spread'] = _clamp(
                d['spread'] + r.uniform(-SPREAD_STEP, SPREAD_STEP), *SPREAD_BOUNDS)
            if storm:
                d['rain'] = _clamp(
                    max(STORM_RAIN_MM, d['rain'] + r.uniform(3, 8)), *RAIN_BOUNDS)
                d['wind'] = _clamp(
                    max(STORM_WIND_M_S, d['wind'] + r.uniform(1, 3)), *WIND_BOUNDS)
            elif fire:
                # Heat wave: hot, bone-dry, breezy — forest fire conditions.
                d['min_c'] = _clamp(
                    max(22.0, d['min_c'] + r.uniform(0.5, 2.0)), *TEMP_BOUNDS)
                d['spread'] = _clamp(
                    max(8.0, d['spread'] + r.uniform(0, 1)), *SPREAD_BOUNDS)
                d['rain'] = 0.0
                d['wind'] = _clamp(
                    max(8.0, d['wind'] + r.uniform(0, 1)), *WIND_BOUNDS)
            elif frost:
                # Cold snap: severe frost, no precipitation.
                d['min_c'] = _clamp(
                    min(-24.0, d['min_c'] - r.uniform(1, 3)), *TEMP_BOUNDS)
                d['rain'] = 0.0
            else:
                # Bounded, mean-reverting walks avoid remaining at storm maxima.
                # Dry spells (high pressure) keep only light, mostly-drying noise.
                rain_noise = r.uniform(-0.3,
                                       0.2) if zone['dry_spell'] else r.uniform(-1, 1)
                d['rain'] = _clamp(d['rain'] + _clamp((rain_target-d['rain'])*0.1 + rain_noise,
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

    def _update_extremes(self, zone: dict[str, Any], forecast: list[dict[str, Any]],
                         timestamp: datetime) -> list[dict[str, Any]]:
        """Derive active alerts from current weather plus accumulated dryness."""
        today = forecast[0]
        rain = today['rainfall_mm']
        total = round(sum(d['rainfall_mm'] for d in forecast), 1)
        high = today['temperature']['max_c']
        wind = today['wind']['speed_m_s']
        low = today['temperature']['min_c']
        zone['dry_ticks'] = zone['dry_ticks'] + \
            1 if rain <= FIRE_MAX_RAIN_MM else 0
        zone['frost_ticks'] = zone['frost_ticks'] + \
            1 if low <= FROSTBITE_MIN_C else 0
        zone['cold_ticks'] = zone['cold_ticks'] + \
            1 if low <= FREEZE_MAX_C else 0
        alerts = zone['alerts']
        zid = zone['id']

        flooding = rain >= FLOOD_DAY_MM or total >= FLOOD_3DAY_MM
        if 'flood' in alerts and not flooding:
            flooding = rain >= FLOOD_CLEAR_MM
        if flooding and high > 0:
            severity = 'severe' if rain >= FLOOD_SEVERE_DAY_MM else 'warning'
            alerts['flood'] = {
                'type': 'flood', 'severity': severity, 'zone_id': zid,
                'started_at': alerts.get('flood', {}).get('started_at', timestamp),
                'description': f'Flood risk: {rain} mm rain today, {total} mm over {FORECAST_DAYS} days',
                'metrics': {'rainfall_today_mm': rain, 'rainfall_3day_mm': total}}
        else:
            alerts.pop('flood', None)

        burning = (
            high >= FIRE_MIN_TEMP_C and zone['dry_ticks'] >= FIRE_DRY_TICKS)
        if 'forest_fire' in alerts and not burning:
            burning = high >= FIRE_CLEAR_TEMP_C and rain <= FIRE_MAX_RAIN_MM
        if burning:
            severity = 'severe' if high >= FIRE_SEVERE_TEMP_C or wind >= 10 else 'warning'
            alerts['forest_fire'] = {
                'type': 'forest_fire', 'severity': severity, 'zone_id': zid,
                'started_at': alerts.get('forest_fire', {}).get('started_at', timestamp),
                'description': f'Forest fire risk: {high} °C, dry for {zone["dry_ticks"]} updates, wind {wind} m/s',
                'metrics': {'max_temperature_c': high, 'dry_ticks': zone['dry_ticks'],
                            'wind_speed_m_s': wind, 'rainfall_today_mm': rain}}
        else:
            alerts.pop('forest_fire', None)

        freezing = low <= FROSTBITE_MIN_C and zone['frost_ticks'] >= FROSTBITE_TICKS
        if 'frostbite' in alerts and not freezing:
            freezing = low <= FROSTBITE_CLEAR_C
        if freezing:
            severity = 'severe' if low <= FROSTBITE_SEVERE_C else 'warning'
            alerts['frostbite'] = {
                'type': 'frostbite', 'severity': severity, 'zone_id': zid,
                'started_at': alerts.get('frostbite', {}).get('started_at', timestamp),
                'description': f'Frostbite risk: {low} °C, severe cold for {zone["frost_ticks"]} updates',
                'metrics': {'min_temperature_c': low,
                            'severe_cold_ticks': zone['frost_ticks']}}
        else:
            alerts.pop('frostbite', None)

        pipes = low <= FREEZE_MAX_C and zone['cold_ticks'] >= FREEZE_TICKS
        if 'freezing_pipes' in alerts and not pipes:
            pipes = low <= FREEZE_MAX_C
        if pipes:
            severity = 'severe' if low <= FREEZE_SEVERE_C else 'warning'
            alerts['freezing_pipes'] = {
                'type': 'freezing_pipes', 'severity': severity, 'zone_id': zid,
                'started_at': alerts.get('freezing_pipes', {}).get('started_at', timestamp),
                'description': f'Freezing pipes risk: {low} °C, sub-zero for {zone["cold_ticks"]} updates',
                'metrics': {'min_temperature_c': low,
                            'sub_zero_ticks': zone['cold_ticks']}}
        else:
            alerts.pop('freezing_pipes', None)
        return [copy.deepcopy(a) for a in alerts.values()]

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
                'weather': copy.deepcopy(frame['weather'][zone_id]),
                'extremes': copy.deepcopy(frame['extremes'][zone_id]), 'estate': copy.deepcopy(house)}

    def generate_events(self) -> list[dict[str, Any]]:
        """Advance every zone once; produce regional and per-house events."""
        with self._lock:
            self._timestamp = self._timestamp + \
                timedelta(minutes=1) if self._timestamp else datetime.now(
                    timezone.utc)
            storm = self._storm_remaining > 0
            fire = self._fire_remaining > 0
            frost = self._frost_remaining > 0
            # True when this tick is the last forced one; the walk then
            # restarts from a mild baseline for the following normal ticks.
            forced_ending = False
            if storm:
                self._storm_remaining -= 1
                forced_ending = forced_ending or self._storm_remaining == 0
            if fire:
                self._fire_remaining -= 1
                forced_ending = forced_ending or self._fire_remaining == 0
            if frost:
                self._frost_remaining -= 1
                forced_ending = forced_ending or self._frost_remaining == 0
            weather = {}
            extremes = {}
            events = []
            for zone_id, zone in self._zones.items():
                self._step(zone, storm, fire, frost)
                weather[zone_id] = self._weather(zone['days'], self._timestamp)
                extremes[zone_id] = self._update_extremes(
                    zone, weather[zone_id]['forecast'], self._timestamp)
                b = zone['bounds_m']
                # Boundary zones are clipped to the configured geographic extent.
                for _ in range(500):
                    lon, lat = _TO_WGS.transform(self._rng.uniform(b['min_x'], b['max_x']),
                                                 self._rng.uniform(b['min_y'], b['max_y']))
                    if self.contains(lat, lon):
                        event = {'timestamp': self._timestamp, 'location': {'latitude': lat, 'longitude': lon},
                                 'zone': self._zone_metadata(zone_id), 'storm': storm,
                                 'weather': copy.deepcopy(weather[zone_id]),
                                 'extremes': copy.deepcopy(extremes[zone_id]), 'estate': None}
                        events.append(event)
                        self.history.append(event)
                        break
            frame = {'timestamp': self._timestamp, 'storm': storm,
                     'weather': weather, 'extremes': extremes}
            self._frames.append(frame)
            for house_id, house in self._houses.items():
                self._house_history[house_id].append(
                    self._house_event(house, frame))
            if forced_ending:
                self._reset_zones_mild()
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
