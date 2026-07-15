import { act, renderHook, waitFor } from '@testing-library/react';
import { beforeEach, describe, expect, it, vi } from 'vitest';

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
  vi.spyOn(console, 'error').mockImplementation(() => undefined);
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

  it('resets loaded state and aborts the active request', () => {
    getMock.mockReturnValueOnce(new Promise(() => undefined));
    const { result } = renderHook(() => useTemperatureData());
    act(() => result.current.fetchData(4, 2026));
    expect(result.current.activeOperation?.mode).toBe('initial');

    act(() => result.current.reset());

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
});
