

"""Forced simulations overwrite stored history and restart the walk mild."""
from data_generator import HISTORY_SIZE, DataGenerator


def house(id=1, latitude=60.2, longitude=24.94):
    return {'id': id, 'user_id': 'test-user', 'address': f'House {id}',
            'latitude': latitude, 'longitude': longitude, 'floor_area_m2': 142.5}


def test_force_storm_instantly_fills_history_with_storm_events():
    gen = DataGenerator(seed=7)
    gen.register_house(house())
    gen.initialize_history(HISTORY_SIZE)
    old_first = gen.latest()[-1]['timestamp']
    gen.force_storm(HISTORY_SIZE)
    # Old events are gone; the history is instantly full of storm ticks.
    regional = gen.latest()
    assert len(regional) >= HISTORY_SIZE  # one event per zone per tick
    assert all(e['storm'] for e in regional)
    assert regional[-1]['timestamp'] >= old_first
    local = gen.latest_for_house(1)
    assert len(local) == HISTORY_SIZE
    assert all(e['storm'] for e in local)
    assert all(e['weather']['forecast'][0]['wind']['speed_m_s'] >= 17
               for e in local)


def test_walk_restarts_mild_after_forced_period():
    gen = DataGenerator(seed=9)
    gen.register_house(house())
    gen.force_frost(3)
    event = gen.latest_for_house(1)[0]
    assert event['weather']['forecast'][0]['temperature']['min_c'] <= -20
    gen.generate_events()  # first normal tick after the forced batch
    event = gen.latest_for_house(1)[0]
    day = event['weather']['forecast'][0]
    assert 0 <= day['temperature']['min_c'] <= 16
    assert day['rainfall_mm'] <= 3
    assert day['wind']['speed_m_s'] <= 8
    assert event['extremes'] == []


def test_new_house_registered_during_storm_gets_only_storm_history():
    gen = DataGenerator(seed=13)
    gen.initialize_history(HISTORY_SIZE)
    gen.force_storm(5)
    gen.register_house(house())
    local = gen.latest_for_house(1)
    assert len(local) == 5
    assert all(e['storm'] for e in local)
