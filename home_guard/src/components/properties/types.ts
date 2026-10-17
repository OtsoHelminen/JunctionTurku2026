export interface ReceivedNotificationInfo {
  title: string | null;
  body: string | null;
  data: Record<string, unknown>;
}

export interface PropertyEntry {
  id: number;
  address: string;
  latitude: number;
  longitude: number;
}

export interface Coordinates {
  latitude: number;
  longitude: number;
}

export interface CityCoordinateBounds {
  minLatitude: number;
  maxLatitude: number;
  minLongitude: number;
  maxLongitude: number;
}
