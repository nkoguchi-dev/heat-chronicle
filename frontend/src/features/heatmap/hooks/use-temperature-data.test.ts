import { act, renderHook, waitFor } from '@testing-library/react';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

import { useTemperatureData } from '@/features/heatmap/hooks/use-temperature-data';
import { apiClient } from '@/features/shared/libs/api-client';
import type { TemperatureRecord, TemperatureResponse } from '@/features/heatmap/types/api';

vi.mock('@/features/shared/libs/api-client', () => ({
  apiClient: { get: vi.fn() },
}));

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

const getMock = vi.mocked(apiClient.get);

beforeEach(() => {
  vi.useFakeTimers({ toFake: ['Date'] });
  vi.setSystemTime(new Date('2026-07-15T00:00:00Z'));
  vi.spyOn(console, 'error').mockImplementation(() => undefined);
});

afterEach(() => {
  vi.useRealTimers();
});

describe('useTemperatureData', () => {
  it('loads initial data and exposes historical pagination metadata', async () => {
    getMock.mockResolvedValueOnce(createResponse());
    const { result } = renderHook(() => useTemperatureData());

    act(() => result.current.fetchData(4, 2026));

    await waitFor(() => expect(result.current.activeOperation).toBeNull());
    expect(result.current.records).toEqual([RECORD]);
    expect(result.current.startYear).toBe(2026);
    expect(result.current.hasOlderData).toBe(true);
    expect(result.current.nextEndYear).toBe(2016);
  });

  it('merges additional historical data', async () => {
    const olderRecord = { ...RECORD, date: '2016-01-01' };
    getMock.mockResolvedValueOnce(createResponse()).mockResolvedValueOnce({
      ...createResponse({ start_year: 2016, next_end_year: 2006 }),
      data: [olderRecord],
    });
    const { result } = renderHook(() => useTemperatureData());
    act(() => result.current.fetchData(4, 2026));
    await waitFor(() => expect(result.current.activeOperation).toBeNull());

    act(() => result.current.fetchMoreData(4, 2016));

    await waitFor(() => expect(result.current.records).toHaveLength(2));
    expect(result.current.records).toEqual([RECORD, olderRecord]);
  });

  it('reports an initial error and retries the failed operation', async () => {
    getMock.mockRejectedValueOnce(new Error('offline')).mockResolvedValueOnce(createResponse());
    const { result } = renderHook(() => useTemperatureData());
    act(() => result.current.fetchData(4, 2026));
    await waitFor(() => expect(result.current.error?.operation.mode).toBe('initial'));

    act(() => result.current.retry());

    await waitFor(() => expect(result.current.records).toEqual([RECORD]));
    expect(result.current.error).toBeNull();
  });

  it('reports a partial failure when a required month cannot be fetched', async () => {
    const fetchedMonths = Array.from({ length: 6 }, (_, index) => `2026-${String(index + 1).padStart(2, '0')}`);
    getMock
      .mockResolvedValueOnce(createResponse({ fetching_required: true, fetched_months: fetchedMonths }))
      .mockRejectedValueOnce(new Error('month failed'));
    const { result } = renderHook(() => useTemperatureData());

    act(() => result.current.fetchData(4, 2026));

    await waitFor(() => expect(result.current.error?.message).toContain('一部の月'));
    expect(result.current.activeOperation).toBeNull();
  });

  it('resets loaded state and ignores the active request abort error', async () => {
    let rejectRequest: (reason?: unknown) => void = () => undefined;
    const request = new Promise<TemperatureResponse>((_resolve, reject) => {
      rejectRequest = reject;
    });
    getMock.mockReturnValueOnce(request);
    const { result } = renderHook(() => useTemperatureData());
    act(() => result.current.fetchData(4, 2026));
    const signal = getMock.mock.calls[0]?.[1]?.signal;
    expect(result.current.activeOperation?.mode).toBe('initial');
    expect(signal?.aborted).toBe(false);

    act(() => result.current.reset());
    await act(async () => {
      rejectRequest(new DOMException('Aborted', 'AbortError'));
      await Promise.resolve();
    });

    expect(signal?.aborted).toBe(true);
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

  it('aborts the active request when the hook unmounts', () => {
    getMock.mockReturnValueOnce(new Promise(() => undefined));
    const { result, unmount } = renderHook(() => useTemperatureData());
    act(() => result.current.fetchData(4, 2026));
    const signal = getMock.mock.calls[0]?.[1]?.signal;

    unmount();

    expect(signal?.aborted).toBe(true);
  });

  it('ignores a stale response after a newer request starts', async () => {
    let resolveFirstRequest: (response: TemperatureResponse) => void = () => undefined;
    const firstRequest = new Promise<TemperatureResponse>((resolve) => {
      resolveFirstRequest = resolve;
    });
    const latestRecord = { ...RECORD, date: '2025-01-01' };
    const latestResponse = {
      ...createResponse({ station_id: 5, start_year: 2025, end_year: 2025 }),
      data: [latestRecord],
    };
    getMock.mockReturnValueOnce(firstRequest).mockResolvedValueOnce(latestResponse);
    const { result } = renderHook(() => useTemperatureData());

    act(() => result.current.fetchData(4, 2026));
    const firstSignal = getMock.mock.calls[0]?.[1]?.signal;
    act(() => result.current.fetchData(5, 2025));

    await waitFor(() => expect(result.current.records).toEqual([latestRecord]));
    expect(firstSignal?.aborted).toBe(true);

    await act(async () => {
      resolveFirstRequest(createResponse());
      await firstRequest;
    });

    expect(result.current.records).toEqual([latestRecord]);
    expect(result.current.error).toBeNull();
  });
});
