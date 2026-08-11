import { act, renderHook } from '@testing-library/react';
import { beforeEach, describe, expect, it, vi } from 'vitest';

import { useHeatmapPage } from '@/features/heatmap/hooks/use-heatmap-page';
import { useStationOptions } from '@/features/heatmap/hooks/use-station-options';
import { useTemperatureData } from '@/features/heatmap/hooks/use-temperature-data';
import { useUrlParams } from '@/features/heatmap/hooks/use-url-params';
import type { UrlParams } from '@/features/heatmap/libs/url-params';
import type { Prefecture, Station } from '@/features/heatmap/types/api';

vi.mock('@/features/heatmap/hooks/use-station-options');
vi.mock('@/features/heatmap/hooks/use-temperature-data');
vi.mock('@/features/heatmap/hooks/use-url-params');

const useStationOptionsMock = vi.mocked(useStationOptions);
const useTemperatureDataMock = vi.mocked(useTemperatureData);
const useUrlParamsMock = vi.mocked(useUrlParams);

const PREFECTURES: Prefecture[] = [
  { prec_no: 44, name: '大分県' },
  { prec_no: 13, name: '東京都' },
];
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
  {
    id: 5,
    station_name: '日田',
    prec_no: 44,
    block_no: '47814',
    station_type: 's',
    latitude: null,
    longitude: null,
    earliest_year: 1942,
  },
];

let params: UrlParams;
let stations: Station[];
const updateUrl = vi.fn();
const fetchData = vi.fn();
const fetchMoreData = vi.fn();
const reset = vi.fn();

beforeEach(() => {
  params = { pref: 44, station: 4, type: 'max' };
  stations = STATIONS;
  useUrlParamsMock.mockImplementation(() => ({ params, updateUrl }));
  useStationOptionsMock.mockImplementation(() => ({
    prefectures: PREFECTURES,
    stations,
    loadingPhase: null,
    error: null,
    retry: vi.fn(),
  }));
  useTemperatureDataMock.mockReturnValue({
    records: [],
    activeOperation: null,
    progress: null,
    error: null,
    hasOlderData: false,
    nextEndYear: null,
    startYear: null,
    fetchData,
    fetchMoreData,
    retry: vi.fn(),
    reset,
  });
});

describe('useHeatmapPage', () => {
  it('restores location changes from URL state without refetching for temperature-only changes', () => {
    const { result, rerender } = renderHook(() => useHeatmapPage());

    expect(reset).toHaveBeenCalledOnce();
    expect(fetchData).toHaveBeenCalledOnce();
    expect(fetchData).toHaveBeenCalledWith(4, new Date().getFullYear());

    params = { ...params, type: 'min' };
    rerender();

    expect(result.current.tempType).toBe('min');
    expect(reset).toHaveBeenCalledOnce();
    expect(fetchData).toHaveBeenCalledOnce();

    params = { ...params, station: 5 };
    rerender();

    expect(result.current.selectedStationId).toBe(5);
    expect(reset).toHaveBeenCalledTimes(2);
    expect(fetchData).toHaveBeenLastCalledWith(5, new Date().getFullYear());
  });

  it('creates one complete history entry for a prefecture and station change', () => {
    const { result, rerender } = renderHook(() => useHeatmapPage());

    act(() => result.current.handlePrefectureChange(13));
    expect(updateUrl).toHaveBeenLastCalledWith({ pref: 13, station: null }, 'push');

    params = { pref: 13, station: null, type: 'max' };
    stations = [];
    rerender();
    const tokyoStation: Station = {
      ...STATIONS[0],
      id: 1,
      station_name: '東京',
      prec_no: 13,
      block_no: '47662',
    };

    act(() => result.current.handleStationSelect(tokyoStation));
    expect(updateUrl).toHaveBeenLastCalledWith({ pref: 13, station: 1 }, 'replace');
  });

  it('pushes same-prefecture station and temperature changes', () => {
    const { result } = renderHook(() => useHeatmapPage());

    act(() => result.current.handleStationSelect(STATIONS[1]));
    expect(updateUrl).toHaveBeenLastCalledWith({ pref: 44, station: 5 }, 'push');

    act(() => result.current.handleTempTypeChange('avg'));
    expect(updateUrl).toHaveBeenLastCalledWith({ type: 'avg' });
  });

  it('replaces an unavailable station with the safe default location', () => {
    params = { pref: 13, station: 999, type: 'min' };
    stations = [{ ...STATIONS[0], id: 1, station_name: '東京', prec_no: 13, block_no: '47662' }];

    renderHook(() => useHeatmapPage());

    expect(updateUrl).toHaveBeenCalledWith({ pref: 44, station: 4 }, 'replace');
    expect(fetchData).not.toHaveBeenCalled();
  });

  it('replaces an unavailable prefecture before resolving its station', () => {
    params = { pref: 99, station: 999, type: 'avg' };
    useStationOptionsMock.mockReturnValue({
      prefectures: PREFECTURES,
      stations: [],
      loadingPhase: 'stations',
      error: null,
      retry: vi.fn(),
    });

    renderHook(() => useHeatmapPage());

    expect(updateUrl).toHaveBeenCalledWith({ pref: 44, station: 4 }, 'replace');
    expect(fetchData).not.toHaveBeenCalled();
  });
});
