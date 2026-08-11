import { act, renderHook, waitFor } from '@testing-library/react';
import { delay, http, HttpResponse } from 'msw';
import { beforeEach, describe, expect, it, vi } from 'vitest';

import { useStationOptions } from '@/features/heatmap/hooks/use-station-options';
import type { Prefecture, Station } from '@/features/heatmap/types/api';
import { server } from '@/test/server';

const API_URL = 'http://localhost:8000';
const PREFECTURES: Prefecture[] = [{ prec_no: 44, name: '大分県' }];
const STATIONS: Station[] = [
  {
    id: 4,
    station_name: '大分',
    prec_no: 44,
    block_no: '47815',
    station_type: 's',
    latitude: null,
    longitude: null,
    earliest_year: 1887,
  },
];
const TOKYO_STATIONS: Station[] = [
  {
    id: 1,
    station_name: '東京',
    prec_no: 13,
    block_no: '47662',
    station_type: 's',
    latitude: null,
    longitude: null,
    earliest_year: 1875,
  },
];

function useSuccessfulStationHandlers(): void {
  server.use(
    http.get(`${API_URL}/api/prefectures`, () => HttpResponse.json(PREFECTURES)),
    http.get(`${API_URL}/api/stations`, ({ request }) => {
      const precNo = new URL(request.url).searchParams.get('prec_no');
      return HttpResponse.json(precNo === '13' ? TOKYO_STATIONS : STATIONS);
    }),
  );
}

beforeEach(() => {
  vi.spyOn(console, 'error').mockImplementation(() => undefined);
});

describe('useStationOptions', () => {
  it('loads the requested HTTP resources', async () => {
    useSuccessfulStationHandlers();
    const { result } = renderHook(() => useStationOptions({ selectedPrecNo: 44 }));

    await waitFor(() => expect(result.current.loadingPhase).toBeNull());
    expect(result.current.prefectures).toEqual(PREFECTURES);
    expect(result.current.stations).toEqual(STATIONS);
  });

  it('reports a prefecture network error and retries successfully', async () => {
    let requestCount = 0;
    server.use(
      http.get(`${API_URL}/api/prefectures`, () => {
        requestCount += 1;
        return requestCount === 1 ? HttpResponse.error() : HttpResponse.json(PREFECTURES);
      }),
    );
    const { result } = renderHook(() => useStationOptions({ selectedPrecNo: null }));

    await waitFor(() => expect(result.current.error?.phase).toBe('prefectures'));
    act(() => result.current.retry());
    await waitFor(() => expect(result.current.prefectures).toEqual(PREFECTURES));
    expect(result.current.error).toBeNull();
    expect(result.current.loadingPhase).toBeNull();
    expect(requestCount).toBe(2);
  });

  it('reports a station HTTP error and retries the current prefecture', async () => {
    let stationRequestCount = 0;
    server.use(
      http.get(`${API_URL}/api/prefectures`, () => HttpResponse.json(PREFECTURES)),
      http.get(`${API_URL}/api/stations`, ({ request }) => {
        expect(new URL(request.url).searchParams.get('prec_no')).toBe('44');
        stationRequestCount += 1;
        return stationRequestCount === 1
          ? HttpResponse.json({ detail: 'temporarily unavailable' }, { status: 503 })
          : HttpResponse.json(STATIONS);
      }),
    );
    const { result } = renderHook(() => useStationOptions({ selectedPrecNo: 44 }));

    await waitFor(() => expect(result.current.error?.phase).toBe('stations'));
    act(() => result.current.retry());
    await waitFor(() => expect(result.current.stations).toEqual(STATIONS));
    expect(result.current.error).toBeNull();
    expect(stationRequestCount).toBe(2);
  });

  it('clears stations when the selected prefecture is removed', async () => {
    useSuccessfulStationHandlers();
    const { result, rerender } = renderHook(({ selectedPrecNo }) => useStationOptions({ selectedPrecNo }), {
      initialProps: { selectedPrecNo: 44 as number | null },
    });
    await waitFor(() => expect(result.current.stations).toEqual(STATIONS));

    rerender({ selectedPrecNo: null });

    await waitFor(() => expect(result.current.stations).toEqual([]));
  });

  it('cancels the previous station HTTP request and keeps the latest response', async () => {
    let oitaRequestWasAborted = false;
    server.use(
      http.get(`${API_URL}/api/prefectures`, () => HttpResponse.json(PREFECTURES)),
      http.get(`${API_URL}/api/stations`, async ({ request }) => {
        const precNo = new URL(request.url).searchParams.get('prec_no');
        if (precNo === '13') return HttpResponse.json(TOKYO_STATIONS);

        request.signal.addEventListener('abort', () => {
          oitaRequestWasAborted = true;
        });
        await delay(100);
        return HttpResponse.json(STATIONS);
      }),
    );
    const { result, rerender } = renderHook(({ selectedPrecNo }) => useStationOptions({ selectedPrecNo }), {
      initialProps: { selectedPrecNo: 44 },
    });
    await waitFor(() => expect(result.current.loadingPhase).toBe('stations'));

    rerender({ selectedPrecNo: 13 });

    await waitFor(() => expect(result.current.stations).toEqual(TOKYO_STATIONS));
    expect(oitaRequestWasAborted).toBe(true);
    expect(result.current.error).toBeNull();
  });
});
