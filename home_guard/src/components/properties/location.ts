import type { House } from '../../api/houses';
import type { CityCoordinateBounds, Coordinates, PropertyEntry } from './types';

const CITY_COORDINATE_BOUNDS: Record<string, CityCoordinateBounds> = {
  Helsinki: { minLatitude: 60.14, maxLatitude: 60.28, minLongitude: 24.85, maxLongitude: 25.15 },
  Espoo: { minLatitude: 60.1, maxLatitude: 60.28, minLongitude: 24.55, maxLongitude: 24.82 },
  Tampere: { minLatitude: 61.42, maxLatitude: 61.58, minLongitude: 23.65, maxLongitude: 23.92 },
  Turku: { minLatitude: 60.4, maxLatitude: 60.52, minLongitude: 22.15, maxLongitude: 22.35 },
  Oulu: { minLatitude: 64.95, maxLatitude: 65.12, minLongitude: 25.35, maxLongitude: 25.65 },
  Jyväskylä: {
    minLatitude: 62.19,
    maxLatitude: 62.3,
    minLongitude: 25.65,
    maxLongitude: 25.85,
  },
  Lahti: { minLatitude: 60.93, maxLatitude: 61.04, minLongitude: 25.55, maxLongitude: 25.75 },
  Kuopio: { minLatitude: 62.84, maxLatitude: 62.97, minLongitude: 27.55, maxLongitude: 27.75 },
  Pori: { minLatitude: 61.44, maxLatitude: 61.54, minLongitude: 21.75, maxLongitude: 21.9 },
  Rovaniemi: { minLatitude: 66.46, maxLatitude: 66.56, minLongitude: 25.65, maxLongitude: 25.85 },
};

export function mapHouseToEntry(house: House): PropertyEntry {
  return {
    id: house.id,
    address: house.address,
    latitude: house.latitude,
    longitude: house.longitude,
  };
}

export function createRandomCoordinates(address: string): Coordinates {
  const city = address.split(',').at(-1)?.trim();
  const bounds = city ? CITY_COORDINATE_BOUNDS[city] : undefined;

  if (!bounds) {
    return {
      latitude: 59.7 + Math.random() * (61.8 - 59.7),
      longitude: 21.0 + Math.random() * (29.5 - 21.0),
    };
  }

  return {
    latitude: bounds.minLatitude + Math.random() * (bounds.maxLatitude - bounds.minLatitude),
    longitude: bounds.minLongitude + Math.random() * (bounds.maxLongitude - bounds.minLongitude),
  };
}
