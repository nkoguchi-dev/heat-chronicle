import { createClockWrapper, FixedClock } from '@/test/fixed-clock';
import { act, renderHook } from '@testing-library/react';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

import { useTemperatureData } from '@/features/heatmap/hooks/use-temperature-data';
import { ApiError, apiClient } from '@/features/shared/libs/api-client';
import type { TemperatureResponse } from '@/features/heatmap/types/api';

vi.mock('@/features/shared/libs/api-client', async (importOriginal) => ({
  ...(await importOriginal<typeof import('@/features/shared/libs/api-client')>()),
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

const wrapper = createClockWrapper(new FixedClock(new Date(2026, 6, 15, 12)));

beforeEach(() => {
  vi.useFakeTimers();
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
    const { result } = renderHook(() => useTemperatureData(), { wrapper });

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
    const { result } = renderHook(() => useTemperatureData(), { wrapper });

    act(() => result.current.fetchData(4, 2026));
    await act(async () => vi.advanceTimersByTimeAsync(0));
    expect(getMock).toHaveBeenCalledTimes(2);

    act(() => result.current.reset());
    await act(async () => vi.advanceTimersByTimeAsync(2000));

    expect(getMock).toHaveBeenCalledTimes(2);
    expect(result.current.activeOperation).toBeNull();
  });
});

describe('temporary capacity failures', () => {
  it.each([
    new ApiError(429, 'busy', 'http', 2),
    new ApiError(503, 'busy', 'http', 2),
    new ApiError(502, 'Bad gateway', 'http', 2),
    new TypeError('network failure'),
  ])('stops monthly requests and waits for manual retry: %s', async (failure) => {
    const record = { date: '2026-07-01', max_temp: 30, min_temp: 20, avg_temp: 25 };
    getMock.mockResolvedValueOnce({ ...createResponse({ fetching_required: true }), data: [record] });
    getMock.mockRejectedValueOnce(failure);
    const { result } = renderHook(() => useTemperatureData(), { wrapper });
    act(() => result.current.fetchData(4, 2026));
    await act(async () => vi.advanceTimersByTimeAsync(0));
    expect(result.current.records).toEqual([record]);
    expect(result.current.error?.retryDisabled).toBe(true);
    act(() => result.current.retry());
    expect(getMock).toHaveBeenCalledTimes(2);
    await act(async () => vi.advanceTimersByTimeAsync(failure instanceof ApiError ? 2000 : 5000));
    expect(getMock).toHaveBeenCalledTimes(2);
    expect(result.current.error?.retryDisabled).toBe(false);
    getMock.mockResolvedValueOnce(createResponse());
    act(() => result.current.retry());
    // Keep existing data while a manual retry starts and after cached response merges.
    expect(result.current.records).toEqual([record]);
    await act(async () => vi.advanceTimersByTimeAsync(0));
    expect(result.current.records).toEqual([record]);
    expect(getMock).toHaveBeenCalledTimes(3);
  });

  it('allows station changes during cooldown and ignores the previous timer', async () => {
    getMock.mockRejectedValueOnce(new ApiError(503, 'busy'));
    const { result } = renderHook(() => useTemperatureData(), { wrapper });
    act(() => result.current.fetchData(4, 2026));
    await act(async () => vi.advanceTimersByTimeAsync(0));
    getMock.mockResolvedValueOnce(createResponse());
    act(() => result.current.fetchData(5, 2026));
    await act(async () => vi.advanceTimersByTimeAsync(5000));
    expect(result.current.error).toBeNull();
    expect(getMock).toHaveBeenCalledTimes(2);
  });
});
