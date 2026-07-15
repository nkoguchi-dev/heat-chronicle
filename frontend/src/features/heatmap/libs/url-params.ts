import type { TempType } from '@/features/heatmap/types/api';

export interface UrlParams {
  station: number | null;
  pref: number | null;
  type: TempType;
}

export interface ParsedUrlParams {
  params: UrlParams;
  usesDefaults: boolean;
}

export const DEFAULT_PREFECTURE_NUMBER = 44;
export const DEFAULT_STATION_ID = 4;

const VALID_TEMP_TYPES: TempType[] = ['max', 'min', 'avg'];

function parsePositiveInteger(value: string | null): number | null {
  if (value === null || !/^\d+$/.test(value)) return null;
  const parsedValue = Number(value);
  return Number.isSafeInteger(parsedValue) && parsedValue > 0 ? parsedValue : null;
}

export function isTempType(value: string | null): value is TempType {
  return value !== null && VALID_TEMP_TYPES.some((temperatureType) => temperatureType === value);
}

export function parseUrlParams(search: string): ParsedUrlParams {
  const searchParams = new URLSearchParams(search);
  const station = parsePositiveInteger(searchParams.get('station'));
  const pref = parsePositiveInteger(searchParams.get('pref'));
  const rawType = searchParams.get('type');
  const type = isTempType(rawType) ? rawType : 'max';

  if (station === null && pref === null) {
    return {
      params: {
        station: DEFAULT_STATION_ID,
        pref: DEFAULT_PREFECTURE_NUMBER,
        type,
      },
      usesDefaults: true,
    };
  }

  return { params: { station, pref, type }, usesDefaults: false };
}

export function applyUrlParams(url: URL, params: Partial<UrlParams>): URL {
  const nextUrl = new URL(url);

  if (params.pref !== undefined) {
    if (params.pref === null) nextUrl.searchParams.delete('pref');
    else nextUrl.searchParams.set('pref', String(params.pref));
  }

  if (params.station !== undefined) {
    if (params.station === null) nextUrl.searchParams.delete('station');
    else nextUrl.searchParams.set('station', String(params.station));
  }

  if (params.type !== undefined) {
    if (params.type === 'max') nextUrl.searchParams.delete('type');
    else nextUrl.searchParams.set('type', params.type);
  }

  return nextUrl;
}
