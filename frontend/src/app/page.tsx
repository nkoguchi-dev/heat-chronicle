"use client";

import { useEffect, useRef, useState } from "react";

import { apiClient } from "@/features/shared/libs/api-client";
import { ThemeToggle } from "@/features/shared/components/theme-toggle";
import { ColorLegend } from "@/features/heatmap/components/ColorLegend";
import { Heatmap } from "@/features/heatmap/components/Heatmap";
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
import type { Prefecture, TempType } from "@/types/api";
import { TEMP_TYPE_LABELS } from "@/types/api";

const DEFAULT_START_YEAR = 1975;

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
  const { records, loading, streaming, progress, error, fetchData } =
    useTemperatureData();

  useEffect(() => {
    apiClient
      .get<Prefecture[]>("/api/prefectures")
      .then(setPrefectures)
      .catch(console.error);
  }, []);

  const restoredRef = useRef(false);
  useEffect(() => {
    if (
      !restoredRef.current &&
      prefectures.length > 0 &&
      initialParams.station != null
    ) {
      restoredRef.current = true;
      fetchData(initialParams.station, DEFAULT_START_YEAR, currentYear);
    }
  }, [prefectures, initialParams.station, fetchData, currentYear]);

  const handleStationSelect = (stationId: number) => {
    setSelectedStationId(stationId);
    fetchData(stationId, DEFAULT_START_YEAR, currentYear);
    updateUrl({ station: stationId, pref: selectedPrecNo });
  };

  const handlePrefectureChange = (precNo: number) => {
    setSelectedPrecNo(precNo);
    updateUrl({ pref: precNo, station: null });
  };

  const handleTempTypeChange = (value: string) => {
    const newType = value as TempType;
    setTempType(newType);
    updateUrl({ type: newType });
  };

  return (
    <div className="flex min-h-screen flex-col items-center gap-6 p-8">
      <div className="flex w-full items-center justify-center relative">
        <h1 className="text-2xl font-bold">Heat Chronicle</h1>
        <div className="absolute right-0">
          <ThemeToggle />
        </div>
      </div>
      <p className="text-muted-foreground">
        日本の観測地点における{TEMP_TYPE_LABELS[tempType]}
        の長期傾向ヒートマップ
      </p>

      <div className="flex items-center gap-4">
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
          <SelectTrigger className="w-[140px]">
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
        {loading && (
          <span className="text-sm text-muted-foreground">読み込み中...</span>
        )}
      </div>

      <ProgressBar progress={progress} streaming={streaming} />

      {error && (
        <div className="rounded border border-destructive bg-destructive/10 px-4 py-2 text-sm text-destructive">
          {error}
        </div>
      )}

      {records.length > 0 && (
        <div className="overflow-x-auto">
          <Heatmap
            records={records}
            startYear={DEFAULT_START_YEAR}
            endYear={currentYear}
            tempType={tempType}
          />
        </div>
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
