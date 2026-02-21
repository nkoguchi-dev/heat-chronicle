"use client";

import { useEffect, useState } from "react";

import { apiClient } from "@/features/shared/libs/api-client";
import { ColorLegend } from "@/features/heatmap/components/ColorLegend";
import { Heatmap } from "@/features/heatmap/components/Heatmap";
import { ProgressBar } from "@/features/heatmap/components/ProgressBar";
import { StationSelector } from "@/features/heatmap/components/StationSelector";
import { useTemperatureData } from "@/hooks/use-temperature-data";
import type { Station } from "@/types/api";

const DEFAULT_START_YEAR = 1975;

export default function Home() {
  const [stations, setStations] = useState<Station[]>([]);
  const [selectedStationId, setSelectedStationId] = useState<number | null>(
    null
  );
  const currentYear = new Date().getFullYear();
  const { records, loading, streaming, progress, error, fetchData } =
    useTemperatureData();

  useEffect(() => {
    apiClient
      .get<Station[]>("/api/stations")
      .then(setStations)
      .catch(console.error);
  }, []);

  const handleStationSelect = (stationId: number) => {
    setSelectedStationId(stationId);
    fetchData(stationId, DEFAULT_START_YEAR, currentYear);
  };

  return (
    <div className="flex min-h-screen flex-col items-center gap-6 p-8">
      <h1 className="text-2xl font-bold">Heat Chronicle</h1>
      <p className="text-muted-foreground">
        日本の主要都市における最高気温の長期傾向ヒートマップ
      </p>

      <div className="flex items-center gap-4">
        <StationSelector
          stations={stations}
          selectedId={selectedStationId}
          onSelect={handleStationSelect}
        />
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
