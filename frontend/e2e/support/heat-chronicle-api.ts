import type { BrowserContext } from '@playwright/test';

import type { Prefecture, Station, TemperatureRecord, TemperatureResponse } from '../../src/features/heatmap/types/api';

const API_ORIGIN = 'http://localhost:8000';
const CURRENT_YEAR = new Date().getFullYear();
const INITIAL_START_YEAR = CURRENT_YEAR - 49;
const OLDER_END_YEAR = CURRENT_YEAR - 50;
const OLDER_START_YEAR = CURRENT_YEAR - 99;

const PREFECTURES: Prefecture[] = [
  { prec_no: 44, name: '大分県' },
  { prec_no: 13, name: '東京都' },
];

const STATIONS: Record<number, Station[]> = {
  44: [createStation(4, '大分', 44, '47815', 1887)],
  13: [createStation(1, '東京', 13, '47662', 1875)],
};

export async function mockHeatChronicleApi(context: BrowserContext): Promise<void> {
  await context.route(`${API_ORIGIN}/**`, async (route) => {
    const request = route.request();
    const url = new URL(request.url());
    if (request.method() !== 'GET') {
      throw new Error(`Unhandled API method: ${request.method()} ${url.toString()}`);
    }

    if (url.pathname === '/api/prefectures') {
      await route.fulfill({ json: PREFECTURES });
      return;
    }

    if (url.pathname === '/api/stations') {
      const prefectureNumber = Number(url.searchParams.get('prec_no'));
      const stations = STATIONS[prefectureNumber];
      if (!stations) throw new Error(`Unhandled prefecture: ${url.toString()}`);
      await route.fulfill({ json: stations });
      return;
    }

    const temperatureMatch = url.pathname.match(/^\/api\/temperature\/(\d+)$/);
    if (temperatureMatch) {
      const stationId = Number(temperatureMatch[1]);
      const endYear = Number(url.searchParams.get('end_year'));
      await route.fulfill({ json: createTemperatureResponse(stationId, endYear) });
      return;
    }

    throw new Error(`Unhandled Heat Chronicle API request: ${url.toString()}`);
  });
}

function createStation(
  id: number,
  stationName: string,
  prefectureNumber: number,
  blockNumber: string,
  earliestYear: number,
): Station {
  return {
    id,
    station_name: stationName,
    prec_no: prefectureNumber,
    block_no: blockNumber,
    station_type: 's',
    latitude: null,
    longitude: null,
    earliest_year: earliestYear,
  };
}

function createTemperatureResponse(stationId: number, endYear: number): TemperatureResponse {
  const station = Object.values(STATIONS)
    .flat()
    .find((candidate) => candidate.id === stationId);
  if (!station) throw new Error(`Unhandled station: ${stationId}`);

  if (endYear === CURRENT_YEAR) {
    const data = [createRecord(CURRENT_YEAR, stationId), createRecord(INITIAL_START_YEAR, stationId + 1)];
    return createResponse(station, INITIAL_START_YEAR, CURRENT_YEAR, true, OLDER_END_YEAR, data);
  }

  if (endYear === OLDER_END_YEAR) {
    const data = [createRecord(OLDER_END_YEAR, stationId + 2), createRecord(OLDER_START_YEAR, stationId + 3)];
    return createResponse(station, OLDER_START_YEAR, OLDER_END_YEAR, false, null, data);
  }

  throw new Error(`Unhandled temperature period: station=${stationId} end_year=${endYear}`);
}

function createResponse(
  station: Station,
  startYear: number,
  endYear: number,
  hasOlderData: boolean,
  nextEndYear: number | null,
  data: TemperatureRecord[],
): TemperatureResponse {
  return {
    metadata: {
      station_id: station.id,
      station_name: station.station_name,
      start_year: startYear,
      end_year: endYear,
      total_records: data.length,
      fetched_months: [],
      fetching_required: false,
      has_older_data: hasOlderData,
      next_end_year: nextEndYear,
    },
    data,
  };
}

function createRecord(year: number, offset: number): TemperatureRecord {
  return {
    date: `${year}-01-01`,
    max_temp: 25 + offset,
    min_temp: 5 + offset,
    avg_temp: 15 + offset,
  };
}

export const browserSmokeYears = {
  current: CURRENT_YEAR,
  initialStart: INITIAL_START_YEAR,
  olderEnd: OLDER_END_YEAR,
  olderStart: OLDER_START_YEAR,
};
