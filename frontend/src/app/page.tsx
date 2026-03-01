"use client";

import { useCallback, useEffect, useState } from "react";

import { apiClient } from "@/features/shared/libs/api-client";
import { ThemeToggle } from "@/features/shared/components/theme-toggle";
import { ColorLegend } from "@/features/heatmap/components/ColorLegend";
import { Heatmap } from "@/features/heatmap/components/Heatmap";
import { LoadMoreButton } from "@/features/heatmap/components/LoadMoreButton";
import { ProgressBar } from "@/features/heatmap/components/ProgressBar";
import { StationSelector } from "@/features/heatmap/components/StationSelector";
import { useTemperatureData } from "@/hooks/use-temperature-data";
import { useUrlParams } from "@/hooks/use-url-params";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import type { Prefecture, Station, TempType } from "@/types/api";
import { TEMP_TYPE_LABELS } from "@/types/api";

export default function Home() {
  const { initialParams, updateUrl } = useUrlParams();
  const [prefectures, setPrefectures] = useState<Prefecture[]>([]);
  const [selectedStationId, setSelectedStationId] = useState<number | null>(
    initialParams.station
  );
  const [selectedPrecNo, setSelectedPrecNo] = useState<number | null>(
    initialParams.pref
  );
  const [tempType, setTempType] = useState<TempType>(initialParams.type);
  const currentYear = new Date().getFullYear();
  const {
    records,
    isLoading,
    isLoadingMore,
    isFetching,
    progress,
    error,
    hasOlderData,
    nextEndYear,
    startYear,
    fetchData,
    fetchMoreData,
  } = useTemperatureData();

  useEffect(() => {
    apiClient
      .get<Prefecture[]>("/api/prefectures")
      .then(setPrefectures)
      .catch(console.error);
  }, []);

  const handleStationSelect = useCallback(
    (station: Station) => {
      setSelectedStationId(station.id);
      fetchData(station.id, currentYear);
      updateUrl({ station: station.id, pref: selectedPrecNo });
    },
    [fetchData, currentYear, selectedPrecNo, updateUrl]
  );

  const handleLoadMore = useCallback(() => {
    if (selectedStationId !== null && nextEndYear !== null) {
      fetchMoreData(selectedStationId, nextEndYear);
    }
  }, [selectedStationId, nextEndYear, fetchMoreData]);

  const handlePrefectureChange = useCallback(
    (precNo: number) => {
      setSelectedPrecNo(precNo);
      updateUrl({ pref: precNo, station: null });
    },
    [updateUrl]
  );

  const handleTempTypeChange = (value: string) => {
    const newType = value as TempType;
    setTempType(newType);
    updateUrl({ type: newType });
  };

  return (
    <div className="flex min-h-screen flex-col items-center gap-4 p-4 md:gap-6 md:p-8">
      <div className="flex w-full items-center justify-center relative">
        <h1 className="text-xl font-bold md:text-2xl">Heat Chronicle</h1>
        <div className="absolute right-0">
          <ThemeToggle />
        </div>
      </div>
      <p className="text-muted-foreground">
        日本の観測地点における{TEMP_TYPE_LABELS[tempType]}
        の長期傾向ヒートマップ
      </p>

      <div className="flex flex-col items-stretch gap-3 w-full max-w-md md:flex-row md:items-center md:w-auto md:max-w-none md:gap-4">
        <StationSelector
          prefectures={prefectures}
          selectedStationId={selectedStationId}
          onSelect={handleStationSelect}
          initialPrecNo={initialParams.pref}
          onPrefectureChange={handlePrefectureChange}
        />
        <Select
          value={tempType}
          onValueChange={handleTempTypeChange}
        >
          <SelectTrigger className="w-full md:w-[140px]">
            <SelectValue />
          </SelectTrigger>
          <SelectContent>
            {(Object.entries(TEMP_TYPE_LABELS) as [TempType, string][]).map(
              ([value, label]) => (
                <SelectItem key={value} value={value}>
                  {label}
                </SelectItem>
              )
            )}
          </SelectContent>
        </Select>
      </div>

      <ProgressBar progress={progress} streaming={isFetching} />

      {error && (
        <div className="rounded border border-destructive bg-destructive/10 px-4 py-2 text-sm text-destructive">
          {error}
        </div>
      )}

      {selectedStationId !== null && startYear !== null && (
        <div className="relative w-full overflow-x-auto">
          <Heatmap
            records={records}
            startYear={startYear}
            endYear={currentYear}
            tempType={tempType}
          />
          {isLoading && (
            <div className="fixed inset-0 z-10 flex items-center justify-center pointer-events-none">
              <div className="h-8 w-8 animate-spin rounded-full border-4 border-muted-foreground/30 border-t-muted-foreground" />
            </div>
          )}
        </div>
      )}

      {hasOlderData && nextEndYear !== null && startYear !== null && (
        <LoadMoreButton
          nextEndYear={nextEndYear}
          loading={isLoadingMore || isFetching}
          onLoadMore={handleLoadMore}
        />
      )}

      {selectedStationId && (
        <div className="flex flex-col items-center gap-2">
          <ColorLegend />
        </div>
      )}

      <footer className="mt-auto pt-8 text-xs text-muted-foreground">
        出典: 気象庁ホームページ (https://www.data.jma.go.jp/)
      </footer>
    </div>
  );
}
