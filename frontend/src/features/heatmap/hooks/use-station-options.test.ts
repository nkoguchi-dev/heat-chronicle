import { act, renderHook, waitFor } from '@testing-library/react';
import { beforeEach, describe, expect, it, vi } from 'vitest';

import { useStationOptions } from '@/features/heatmap/hooks/use-station-options';
import { apiClient } from '@/features/shared/libs/api-client';
import type { Prefecture, Station } from '@/features/heatmap/types/api';

vi.mock('@/features/shared/libs/api-client', () => ({
  apiClient: { get: vi.fn() },
}));

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

const getMock = vi.mocked(apiClient.get);

beforeEach(() => {
  vi.spyOn(console, 'error').mockImplementation(() => undefined);
});

describe('useStationOptions', () => {
  it('loads prefectures and stations and resolves the initial station once', async () => {
    const onInitialStationResolved = vi.fn();
    getMock.mockResolvedValueOnce(PREFECTURES).mockResolvedValueOnce(STATIONS);

    const { result } = renderHook(() =>
      useStationOptions({ selectedPrecNo: 44, initialStationId: 4, onInitialStationResolved }),
    );

    await waitFor(() => expect(result.current.loadingPhase).toBeNull());
    expect(result.current.prefectures).toEqual(PREFECTURES);
    expect(result.current.stations).toEqual(STATIONS);
    expect(onInitialStationResolved).toHaveBeenCalledOnce();
    expect(onInitialStationResolved).toHaveBeenCalledWith(STATIONS[0]);
  });

  it('reports a prefecture error and retries successfully', async () => {
    getMock.mockRejectedValueOnce(new Error('offline')).mockResolvedValueOnce(PREFECTURES);
    const { result } = renderHook(() =>
      useStationOptions({ selectedPrecNo: null, initialStationId: null, onInitialStationResolved: vi.fn() }),
    );

    await waitFor(() => expect(result.current.error?.phase).toBe('prefectures'));
    act(() => result.current.retry());
    await waitFor(() => expect(result.current.prefectures).toEqual(PREFECTURES));
    expect(result.current.error).toBeNull();
    expect(result.current.loadingPhase).toBeNull();
  });

  it('reports a station error and retries the current prefecture', async () => {
    getMock
      .mockResolvedValueOnce(PREFECTURES)
      .mockRejectedValueOnce(new Error('offline'))
      .mockResolvedValueOnce(STATIONS);
    const { result } = renderHook(() =>
      useStationOptions({ selectedPrecNo: 44, initialStationId: null, onInitialStationResolved: vi.fn() }),
    );

    await waitFor(() => expect(result.current.error?.phase).toBe('stations'));
    act(() => result.current.retry());
    await waitFor(() => expect(result.current.stations).toEqual(STATIONS));
    expect(result.current.error).toBeNull();
  });

  it('clears stations when the selected prefecture is removed', async () => {
    getMock.mockResolvedValueOnce(PREFECTURES).mockResolvedValueOnce(STATIONS);
    const { result, rerender } = renderHook(
      ({ selectedPrecNo }) =>
        useStationOptions({ selectedPrecNo, initialStationId: null, onInitialStationResolved: vi.fn() }),
      { initialProps: { selectedPrecNo: 44 as number | null } },
    );
    await waitFor(() => expect(result.current.stations).toEqual(STATIONS));

    rerender({ selectedPrecNo: null });

    await waitFor(() => expect(result.current.stations).toEqual([]));
  });
});
