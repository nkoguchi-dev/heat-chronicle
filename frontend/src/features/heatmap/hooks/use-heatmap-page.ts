'use client';

import { useCallback, useEffect } from 'react';

import { useStationOptions, type StationOptionsLoadPhase } from './use-station-options';
import { useTemperatureData } from './use-temperature-data';
import { useUrlParams } from './use-url-params';

import { DEFAULT_PREFECTURE_NUMBER, DEFAULT_STATION_ID, isTempType } from '../libs/url-params';
import type { ProgressEvent, Station, TemperatureRecord, TempType } from '../types/api';
import type { TemperatureLoadError, TemperatureLoadOperation } from '../types/temperature-data';

interface UseHeatmapPageReturn {
  selectedStationId: number | null;
  selectedPrecNo: number | null;
  tempType: TempType;
  currentYear: number;
  records: TemperatureRecord[];
  activeOperation: TemperatureLoadOperation | null;
  progress: ProgressEvent | null;
  temperatureError: TemperatureLoadError | null;
  hasOlderData: boolean;
  nextEndYear: number | null;
  startYear: number | null;
  stationOptions: ReturnType<typeof useStationOptions>;
  handleStationSelect: (station: Station) => void;
  handleLoadMore: () => void;
  handlePrefectureChange: (precNo: number) => void;
  handleTempTypeChange: (value: string) => void;
  retryTemperature: () => void;
  stationOptionsLoadingPhase: StationOptionsLoadPhase | null;
}

export function useHeatmapPage(): UseHeatmapPageReturn {
  const { params, updateUrl } = useUrlParams();
  const currentYear = new Date().getFullYear();
  const temperature = useTemperatureData();
  const { fetchData, fetchMoreData, nextEndYear, reset } = temperature;
  const stationOptions = useStationOptions({ selectedPrecNo: params.pref });

  useEffect(() => {
    reset();
  }, [params.pref, params.station, reset]);

  useEffect(() => {
    if (params.pref === null || stationOptions.loadingPhase === 'prefectures') return;
    if (stationOptions.error?.phase === 'prefectures') return;

    const hasSelectedPrefecture = stationOptions.prefectures.some((prefecture) => prefecture.prec_no === params.pref);
    if (!hasSelectedPrefecture && params.pref !== DEFAULT_PREFECTURE_NUMBER) {
      updateUrl({ pref: DEFAULT_PREFECTURE_NUMBER, station: DEFAULT_STATION_ID }, 'replace');
    }
  }, [params.pref, stationOptions.error, stationOptions.loadingPhase, stationOptions.prefectures, updateUrl]);

  useEffect(() => {
    if (params.pref === null || params.station === null || stationOptions.loadingPhase !== null) return;
    if (stationOptions.error !== null) return;

    const station = stationOptions.stations.find(
      (candidate) => candidate.id === params.station && candidate.prec_no === params.pref,
    );
    if (station) {
      fetchData(station.id, currentYear);
      return;
    }

    if (params.pref !== DEFAULT_PREFECTURE_NUMBER || params.station !== DEFAULT_STATION_ID) {
      updateUrl({ pref: DEFAULT_PREFECTURE_NUMBER, station: DEFAULT_STATION_ID }, 'replace');
    }
  }, [
    currentYear,
    fetchData,
    params.pref,
    params.station,
    stationOptions.error,
    stationOptions.loadingPhase,
    stationOptions.stations,
    updateUrl,
  ]);

  const handleStationSelect = useCallback(
    (station: Station): void => {
      updateUrl({ station: station.id, pref: station.prec_no }, params.station === null ? 'replace' : 'push');
    },
    [params.station, updateUrl],
  );

  const handleLoadMore = useCallback((): void => {
    if (params.station !== null && nextEndYear !== null) {
      fetchMoreData(params.station, nextEndYear);
    }
  }, [fetchMoreData, nextEndYear, params.station]);

  const handlePrefectureChange = useCallback(
    (precNo: number): void => {
      updateUrl({ pref: precNo, station: null }, params.station === null ? 'replace' : 'push');
    },
    [params.station, updateUrl],
  );

  const handleTempTypeChange = (value: string): void => {
    if (!isTempType(value)) return;
    updateUrl({ type: value });
  };

  return {
    selectedStationId: params.station,
    selectedPrecNo: params.pref,
    tempType: params.type,
    currentYear,
    records: temperature.records,
    activeOperation: temperature.activeOperation,
    progress: temperature.progress,
    temperatureError: temperature.error,
    hasOlderData: temperature.hasOlderData,
    nextEndYear: temperature.nextEndYear,
    startYear: temperature.startYear,
    stationOptions,
    handleStationSelect,
    handleLoadMore,
    handlePrefectureChange,
    handleTempTypeChange,
    retryTemperature: temperature.retry,
    stationOptionsLoadingPhase: stationOptions.loadingPhase,
  };
}
