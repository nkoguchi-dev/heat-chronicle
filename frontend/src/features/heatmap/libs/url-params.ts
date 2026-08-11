import type { TempType } from '@/features/heatmap/types/api';

export interface UrlParams {
  station: number | null;
  pref: number | null;
  type: TempType;
}

export interface ParsedUrlParams {
  params: UrlParams;
  needsNormalization: boolean;
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
  const rawStation = searchParams.get('station');
  const rawPref = searchParams.get('pref');
  const station = parsePositiveInteger(rawStation);
  const pref = parsePositiveInteger(rawPref);
  const rawType = searchParams.get('type');
  const type = isTempType(rawType) ? rawType : 'max';
  const hasCompleteLocation = pref !== null && station !== null;
  const hasPrefectureSelection = pref !== null && rawStation === null;

  if (!hasCompleteLocation && !hasPrefectureSelection) {
    return {
      params: {
        station: DEFAULT_STATION_ID,
        pref: DEFAULT_PREFECTURE_NUMBER,
        type,
      },
      needsNormalization: true,
    };
  }

  return {
    params: { station, pref, type },
    needsNormalization: (rawType !== null && !isTempType(rawType)) || rawType === 'max',
  };
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
