import { API_URL } from './config';
import { withTimeout } from './http';

export interface House {
  id: number;
  user_id: string;
  address: string;
  latitude: number;
  longitude: number;
  construction_year: number | null;
  house_type: string | null;
  floor_area_m2: number | null;
  number_of_floors: number | null;
  condition: string | null;
  created_at: string;
}

export interface CreateHousePayload {
  address: string;
  latitude: number;
  longitude: number;
}

interface HousesResponse {
  houses: House[];
}

interface HouseResponse {
  house: House;
}

async function readResponse<T>(response: Response): Promise<T> {
  const body = (await response.json()) as T | { detail?: string };
  if (!response.ok) {
    const detail =
      typeof body === 'object' && body !== null && 'detail' in body ? body.detail : undefined;
    throw new Error(
      typeof detail === 'string' ? detail : `House request failed (${response.status}).`
    );
  }
  return body as T;
}

// The timeout covers reading the body too, not just the response headers
function requestJson<T>(path: string, init: RequestInit = {}): Promise<T> {
  return withTimeout(
    async (signal) => readResponse<T>(await fetch(`${API_URL}${path}`, { ...init, signal })),
    { signal: init.signal ?? undefined }
  );
}

export async function fetchHouses(signal?: AbortSignal): Promise<House[]> {
  const result = await requestJson<HousesResponse>('/app/houses', { signal });
  if (!Array.isArray(result.houses)) {
    throw new Error('The houses response has an invalid format.');
  }
  return result.houses;
}

export async function createHouse(
  payload: CreateHousePayload,
  signal?: AbortSignal
): Promise<House> {
  const result = await requestJson<HouseResponse>('/app/houses', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ user_id: 'system', ...payload }),
    signal,
  });
  if (!result.house || typeof result.house.id !== 'number') {
    throw new Error('The created house response has an invalid format.');
  }
  return result.house;
}
