"use client";

import { useCallback, useEffect, useState } from "react";
import { Github } from "lucide-react";

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
        <div className="w-full">
          <p
            id="heatmap-scroll-hint"
            className="mb-2 text-center text-xs text-muted-foreground md:hidden"
          >
            横にスクロールして期間を確認できます
            <span aria-hidden="true"> →</span>
          </p>
          <div
            className="relative w-full overflow-x-auto"
            role="region"
            aria-label="気温ヒートマップ"
            aria-describedby="heatmap-scroll-hint"
            tabIndex={0}
          >
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

      <footer className="mt-auto flex flex-wrap items-center justify-center gap-x-3 gap-y-2 pt-8 text-xs text-muted-foreground">
        <span>
          データ出典: {" "}
          <a
            href="https://www.data.jma.go.jp/"
            target="_blank"
            rel="noopener noreferrer"
            className="underline underline-offset-4 transition-colors hover:text-foreground"
          >
            気象庁ホームページ
          </a>
        </span>
        <span aria-hidden="true" className="hidden text-border sm:inline">
          |
        </span>
        <a
          href="https://github.com/nkoguchi-dev/heat-chronicle"
          target="_blank"
          rel="noopener noreferrer"
          className="inline-flex items-center gap-1.5 font-medium text-foreground underline-offset-4 transition-colors hover:underline"
          aria-label="Heat ChronicleのソースコードをGitHubで開く（新しいタブ）"
        >
          <Github aria-hidden="true" className="h-3.5 w-3.5" />
          GitHub
        </a>
      </footer>
    </div>
  );
}
