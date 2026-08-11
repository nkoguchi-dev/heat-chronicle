'use client';

import { useCallback, useState } from 'react';

import { useStationOptions, type StationOptionsLoadPhase } from './use-station-options';
import { useTemperatureData } from './use-temperature-data';
import { useUrlParams } from './use-url-params';

import { isTempType } from '../libs/url-params';
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
  const { initialParams, updateUrl } = useUrlParams();
  const [selectedStationId, setSelectedStationId] = useState<number | null>(initialParams.station);
  const [selectedPrecNo, setSelectedPrecNo] = useState<number | null>(initialParams.pref);
  const [tempType, setTempType] = useState<TempType>(initialParams.type);
  const currentYear = new Date().getFullYear();
  const temperature = useTemperatureData();
  const { fetchData, fetchMoreData, nextEndYear, reset } = temperature;

  const handleStationSelect = useCallback(
    (station: Station): void => {
      setSelectedStationId(station.id);
      fetchData(station.id, currentYear);
      updateUrl({ station: station.id, pref: selectedPrecNo });
    },
    [currentYear, fetchData, selectedPrecNo, updateUrl],
  );

  const stationOptions = useStationOptions({
    selectedPrecNo,
    initialStationId: initialParams.station,
    onInitialStationResolved: handleStationSelect,
  });

  const handleLoadMore = useCallback((): void => {
    if (selectedStationId !== null && nextEndYear !== null) {
      fetchMoreData(selectedStationId, nextEndYear);
    }
  }, [fetchMoreData, nextEndYear, selectedStationId]);

  const handlePrefectureChange = useCallback(
    (precNo: number): void => {
      reset();
      setSelectedStationId(null);
      setSelectedPrecNo(precNo);
      updateUrl({ pref: precNo, station: null });
    },
    [reset, updateUrl],
  );

  const handleTempTypeChange = (value: string): void => {
    if (!isTempType(value)) return;
    setTempType(value);
    updateUrl({ type: value });
  };

  return {
    selectedStationId,
    selectedPrecNo,
    tempType,
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
