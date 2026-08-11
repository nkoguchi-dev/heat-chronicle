import { act, renderHook } from '@testing-library/react';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

import { useTemperatureData } from '@/features/heatmap/hooks/use-temperature-data';
import { apiClient } from '@/features/shared/libs/api-client';
import type { TemperatureResponse } from '@/features/heatmap/types/api';

vi.mock('@/features/shared/libs/api-client', () => ({
  apiClient: { get: vi.fn() },
}));

function createResponse(overrides: Partial<TemperatureResponse['metadata']> = {}): TemperatureResponse {
  return {
    metadata: {
      station_id: 4,
      station_name: '大分',
      start_year: 2026,
      end_year: 2026,
      total_records: 0,
      fetched_months: [],
      fetching_required: false,
      has_older_data: true,
      next_end_year: 2016,
      ...overrides,
    },
    data: [],
  };
}

const getMock = vi.mocked(apiClient.get);

beforeEach(() => {
  vi.useFakeTimers();
  vi.setSystemTime(new Date('2026-07-15T00:00:00Z'));
});

afterEach(() => {
  vi.useRealTimers();
});

describe('useTemperatureData request pacing', () => {
  it('waits two seconds between monthly fetch requests', async () => {
    const fetchedMonths = Array.from({ length: 5 }, (_, index) => `2026-${String(index + 1).padStart(2, '0')}`);
    getMock
      .mockResolvedValueOnce(createResponse({ fetching_required: true, fetched_months: fetchedMonths }))
      .mockResolvedValueOnce({ year: 2026, month: 7, records: [] })
      .mockResolvedValueOnce({ year: 2026, month: 6, records: [] });
    const { result } = renderHook(() => useTemperatureData());

    act(() => result.current.fetchData(4, 2026));
    await act(async () => vi.advanceTimersByTimeAsync(0));
    expect(getMock).toHaveBeenCalledTimes(2);

    await act(async () => vi.advanceTimersByTimeAsync(1999));
    expect(getMock).toHaveBeenCalledTimes(2);

    await act(async () => vi.advanceTimersByTimeAsync(1));
    expect(getMock).toHaveBeenCalledTimes(3);
    expect(result.current.activeOperation).toBeNull();
  });

  it('cancels the wait before the next monthly fetch request', async () => {
    const fetchedMonths = Array.from({ length: 5 }, (_, index) => `2026-${String(index + 1).padStart(2, '0')}`);
    getMock
      .mockResolvedValueOnce(createResponse({ fetching_required: true, fetched_months: fetchedMonths }))
      .mockResolvedValueOnce({ year: 2026, month: 7, records: [] });
    const { result } = renderHook(() => useTemperatureData());

    act(() => result.current.fetchData(4, 2026));
    await act(async () => vi.advanceTimersByTimeAsync(0));
    expect(getMock).toHaveBeenCalledTimes(2);

    act(() => result.current.reset());
    await act(async () => vi.advanceTimersByTimeAsync(2000));

    expect(getMock).toHaveBeenCalledTimes(2);
    expect(result.current.activeOperation).toBeNull();
  });
});
