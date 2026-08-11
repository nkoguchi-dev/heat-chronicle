import { act, renderHook, waitFor } from '@testing-library/react';
import { delay, http, HttpResponse } from 'msw';
import { beforeEach, describe, expect, it, vi } from 'vitest';

import { useTemperatureData } from '@/features/heatmap/hooks/use-temperature-data';
import type { TemperatureRecord, TemperatureResponse } from '@/features/heatmap/types/api';
import { server } from '@/test/server';

const API_URL = 'http://localhost:8000';
const RECORD: TemperatureRecord = {
  date: '2026-01-01',
  max_temp: 10,
  min_temp: 0,
  avg_temp: 5,
};

function createResponse(overrides: Partial<TemperatureResponse['metadata']> = {}): TemperatureResponse {
  return {
    metadata: {
      station_id: 4,
      station_name: '大分',
      start_year: 2026,
      end_year: 2026,
      total_records: 1,
      fetched_months: [],
      fetching_required: false,
      has_older_data: true,
      next_end_year: 2016,
      ...overrides,
    },
    data: [RECORD],
  };
}

beforeEach(() => {
  vi.spyOn(console, 'error').mockImplementation(() => undefined);
});

describe('useTemperatureData HTTP integration', () => {
  it('loads initial data from the requested station and year', async () => {
    server.use(
      http.get(`${API_URL}/api/temperature/4`, ({ request }) => {
        expect(new URL(request.url).searchParams.get('end_year')).toBe('2026');
        return HttpResponse.json(createResponse());
      }),
    );
    const { result } = renderHook(() => useTemperatureData());

    act(() => result.current.fetchData(4, 2026));

    await waitFor(() => expect(result.current.activeOperation).toBeNull());
    expect(result.current.records).toEqual([RECORD]);
    expect(result.current).toMatchObject({ startYear: 2026, hasOlderData: true, nextEndYear: 2016 });
  });

  it('reports an HTTP error and retries the same operation', async () => {
    let requestCount = 0;
    server.use(
      http.get(`${API_URL}/api/temperature/4`, () => {
        requestCount += 1;
        return requestCount === 1
          ? HttpResponse.json({ detail: 'temporarily unavailable' }, { status: 503 })
          : HttpResponse.json(createResponse());
      }),
    );
    const { result } = renderHook(() => useTemperatureData());
    act(() => result.current.fetchData(4, 2026));
    await waitFor(() => expect(result.current.error?.operation.mode).toBe('initial'));

    act(() => result.current.retry());

    await waitFor(() => expect(result.current.records).toEqual([RECORD]));
    expect(result.current.error).toBeNull();
    expect(requestCount).toBe(2);
  });

  it('reports a partial failure from the monthly HTTP boundary', async () => {
    const fetchedMonths = Array.from({ length: 7 }, (_, index) => `2026-${String(index + 1).padStart(2, '0')}`);
    server.use(
      http.get(`${API_URL}/api/temperature/4`, () =>
        HttpResponse.json(createResponse({ fetching_required: true, fetched_months: fetchedMonths })),
      ),
      http.get(`${API_URL}/api/temperature/4/fetch-month`, ({ request }) => {
        const url = new URL(request.url);
        expect(url.searchParams.get('year')).toBe('2026');
        expect(url.searchParams.get('month')).toBe('8');
        return HttpResponse.json({ detail: 'month failed' }, { status: 503 });
      }),
    );
    const { result } = renderHook(() => useTemperatureData());

    act(() => result.current.fetchData(4, 2026));

    await waitFor(() => expect(result.current.error?.message).toContain('一部の月'));
    expect(result.current.activeOperation).toBeNull();
  });

  it('cancels a stale request and keeps the latest station response', async () => {
    let firstRequestStarted = false;
    let firstRequestWasAborted = false;
    const latestRecord = { ...RECORD, date: '2025-01-01' };
    server.use(
      http.get(`${API_URL}/api/temperature/:stationId`, async ({ params, request }) => {
        if (params.stationId === '5') {
          return HttpResponse.json({
            ...createResponse({ station_id: 5, start_year: 2025, end_year: 2025 }),
            data: [latestRecord],
          });
        }
        firstRequestStarted = true;
        request.signal.addEventListener('abort', () => {
          firstRequestWasAborted = true;
        });
        await delay(100);
        return HttpResponse.json(createResponse());
      }),
    );
    const { result } = renderHook(() => useTemperatureData());
    act(() => result.current.fetchData(4, 2026));
    await waitFor(() => expect(firstRequestStarted).toBe(true));
    act(() => result.current.fetchData(5, 2025));

    await waitFor(() => expect(result.current.records).toEqual([latestRecord]));
    expect(firstRequestWasAborted).toBe(true);
    expect(result.current.error).toBeNull();
  });

  it('does not update state after reset cancels an active request', async () => {
    let requestWasAborted = false;
    server.use(
      http.get(`${API_URL}/api/temperature/4`, async ({ request }) => {
        request.signal.addEventListener('abort', () => {
          requestWasAborted = true;
        });
        await delay(100);
        return HttpResponse.json(createResponse());
      }),
    );
    const { result } = renderHook(() => useTemperatureData());
    act(() => result.current.fetchData(4, 2026));
    await waitFor(() => expect(result.current.activeOperation?.mode).toBe('initial'));

    act(() => result.current.reset());

    await waitFor(() => expect(requestWasAborted).toBe(true));
    expect(result.current).toMatchObject({
      records: [],
      activeOperation: null,
      progress: null,
      error: null,
      hasOlderData: false,
      nextEndYear: null,
      startYear: null,
    });
  });

  it('prevents duplicate historical data requests while one is active', async () => {
    let historicalRequestCount = 0;
    const olderRecord = { ...RECORD, date: '2016-01-01' };
    server.use(
      http.get(`${API_URL}/api/temperature/4`, async ({ request }) => {
        const endYear = new URL(request.url).searchParams.get('end_year');
        if (endYear === '2026') return HttpResponse.json(createResponse());
        historicalRequestCount += 1;
        await delay(50);
        return HttpResponse.json({
          ...createResponse({ start_year: 2016, end_year: 2016, next_end_year: 2006 }),
          data: [olderRecord],
        });
      }),
    );
    const { result } = renderHook(() => useTemperatureData());
    act(() => result.current.fetchData(4, 2026));
    await waitFor(() => expect(result.current.activeOperation).toBeNull());

    act(() => {
      result.current.fetchMoreData(4, 2016);
      result.current.fetchMoreData(4, 2016);
    });

    await waitFor(() => expect(result.current.records).toEqual([RECORD, olderRecord]));
    expect(historicalRequestCount).toBe(1);
  });
});
