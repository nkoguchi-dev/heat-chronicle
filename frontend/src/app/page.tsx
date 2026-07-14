"use client";

import { useCallback, useState } from "react";
import { Github } from "lucide-react";

import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { ColorLegend } from "@/features/heatmap/components/ColorLegend";
import { Heatmap } from "@/features/heatmap/components/Heatmap";
import { LoadingStatus } from "@/features/heatmap/components/LoadingStatus";
import { LoadMoreButton } from "@/features/heatmap/components/LoadMoreButton";
import { StationSelector } from "@/features/heatmap/components/StationSelector";
import { ThemeToggle } from "@/features/shared/components/theme-toggle";
import { useStationOptions } from "@/hooks/use-station-options";
import { useTemperatureData } from "@/hooks/use-temperature-data";
import { useUrlParams } from "@/hooks/use-url-params";
import type { Station, TempType } from "@/types/api";
import { TEMP_TYPE_LABELS } from "@/types/api";

export default function Home() {
  const { initialParams, updateUrl } = useUrlParams();
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
    activeOperation,
    progress,
    error: temperatureError,
    hasOlderData,
    nextEndYear,
    startYear,
    fetchData,
    fetchMoreData,
    retry: retryTemperature,
    reset: resetTemperature,
  } = useTemperatureData();

  const handleStationSelect = useCallback(
    (station: Station) => {
      setSelectedStationId(station.id);
      fetchData(station.id, currentYear);
      updateUrl({ station: station.id, pref: selectedPrecNo });
    },
    [fetchData, currentYear, selectedPrecNo, updateUrl]
  );

  const {
    prefectures,
    stations,
    loadingPhase: stationOptionsLoadingPhase,
    error: stationOptionsError,
    retry: retryStationOptions,
  } = useStationOptions({
    selectedPrecNo,
    initialStationId: initialParams.station,
    onInitialStationResolved: handleStationSelect,
  });

  const handleLoadMore = useCallback(() => {
    if (selectedStationId !== null && nextEndYear !== null) {
      fetchMoreData(selectedStationId, nextEndYear);
    }
  }, [selectedStationId, nextEndYear, fetchMoreData]);

  const handlePrefectureChange = useCallback(
    (precNo: number) => {
      resetTemperature();
      setSelectedStationId(null);
      setSelectedPrecNo(precNo);
      updateUrl({ pref: precNo, station: null });
    },
    [resetTemperature, updateUrl]
  );

  const handleTempTypeChange = (value: string) => {
    const newType = value as TempType;
    setTempType(newType);
    updateUrl({ type: newType });
  };

  const initialTemperatureLoading = activeOperation?.mode === "initial";
  const moreTemperatureLoading = activeOperation?.mode === "more";
  const initialTemperatureError =
    temperatureError?.operation.mode === "initial" ? temperatureError : null;
  const moreTemperatureError =
    temperatureError?.operation.mode === "more" ? temperatureError : null;
  const loadingMoreEndYear = moreTemperatureLoading
    ? activeOperation.endYear
    : nextEndYear;
  const singleMonthProgress =
    initialTemperatureLoading && progress?.total === 1 ? progress : null;

  const primaryStatus = stationOptionsError ? (
    <LoadingStatus
      state="error"
      message={stationOptionsError.message}
      onRetry={retryStationOptions}
    />
  ) : stationOptionsLoadingPhase ? (
    <LoadingStatus
      state="loading"
      message={
        stationOptionsLoadingPhase === "prefectures"
          ? "都道府県一覧を読み込んでいます..."
          : "観測地点一覧を読み込んでいます..."
      }
    />
  ) : initialTemperatureError ? (
    <LoadingStatus
      state="error"
      message={initialTemperatureError.message}
      onRetry={retryTemperature}
    />
  ) : initialTemperatureLoading && singleMonthProgress === null ? (
    <LoadingStatus
      state={progress ? "progress" : "loading"}
      message={
        progress
          ? `${progress.year}年${progress.month}月を取得中...`
          : "気温データを読み込んでいます..."
      }
      progress={progress ?? undefined}
    />
  ) : null;

  const loadMoreStatus = moreTemperatureError ? (
    <LoadingStatus
      state="error"
      message={moreTemperatureError.message}
      onRetry={retryTemperature}
    />
  ) : moreTemperatureLoading ? (
    <LoadingStatus
      state={progress ? "progress" : "loading"}
      message={
        progress
          ? `${progress.year}年${progress.month}月を取得中...`
          : `〜${activeOperation.endYear}年のデータを読み込んでいます...`
      }
      progress={progress ?? undefined}
    />
  ) : null;

  return (
    <div
      className="flex min-h-screen flex-col items-center gap-4 p-4 md:gap-6 md:p-8"
      aria-busy={
        stationOptionsLoadingPhase !== null || activeOperation !== null
      }
    >
      <div className="relative flex w-full items-center justify-center">
        <h1 className="text-xl font-bold md:text-2xl">Heat Chronicle</h1>
        <div className="absolute right-0 flex items-center gap-2">
          {singleMonthProgress && (
            <LoadingStatus
              state="progress"
              message={`${singleMonthProgress.year}年${singleMonthProgress.month}月を取得中...`}
              progress={singleMonthProgress}
              variant="compact"
            />
          )}
          <ThemeToggle />
        </div>
      </div>
      <p className="text-muted-foreground">
        日本の観測地点における{TEMP_TYPE_LABELS[tempType]}
        の長期傾向ヒートマップ
      </p>

      <div className="flex w-full max-w-md flex-col items-stretch gap-3 md:w-auto md:max-w-none md:flex-row md:items-center md:gap-4">
        <StationSelector
          prefectures={prefectures}
          stations={stations}
          selectedPrecNo={selectedPrecNo}
          selectedStationId={selectedStationId}
          loadingPrefectures={stationOptionsLoadingPhase === "prefectures"}
          loadingStations={stationOptionsLoadingPhase === "stations"}
          onSelect={handleStationSelect}
          onPrefectureChange={handlePrefectureChange}
        />
        <Select value={tempType} onValueChange={handleTempTypeChange}>
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

      {primaryStatus}

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
          </div>
        </div>
      )}

      {loadMoreStatus}

      {moreTemperatureError === null &&
        loadingMoreEndYear !== null &&
        startYear !== null &&
        (hasOlderData || moreTemperatureLoading) && (
          <LoadMoreButton
            nextEndYear={loadingMoreEndYear}
            loading={moreTemperatureLoading}
            onLoadMore={handleLoadMore}
          />
        )}

      {selectedStationId !== null && startYear !== null && (
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
