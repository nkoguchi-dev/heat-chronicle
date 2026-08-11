'use client';

import { ColorLegend } from './components/ColorLegend';
import { HeatmapControls } from './components/HeatmapControls';
import { HeatmapFooter } from './components/HeatmapFooter';
import { HeatmapHeader } from './components/HeatmapHeader';
import { HeatmapViewport } from './components/HeatmapViewport';
import { LoadMoreButton } from './components/LoadMoreButton';
import { LoadMoreStatus } from './components/LoadMoreStatus';
import { PrimaryLoadingStatus } from './components/PrimaryLoadingStatus';
import { useHeatmapPage } from './hooks/use-heatmap-page';
import { TEMP_TYPE_LABELS } from './types/api';

export function HeatmapPage(): React.JSX.Element {
  const page = useHeatmapPage();
  const singleMonthProgress =
    page.activeOperation?.mode === 'initial' && page.progress?.total === 1 ? page.progress : null;

  return (
    <div
      className="flex min-h-screen flex-col items-center gap-4 p-4 md:gap-6 md:p-8"
      aria-busy={page.stationOptionsLoadingPhase !== null || page.activeOperation !== null}
    >
      <HeatmapHeader progress={singleMonthProgress} />
      <p className="text-muted-foreground">
        日本の観測地点における{TEMP_TYPE_LABELS[page.tempType]}の長期傾向ヒートマップ
      </p>
      <HeatmapControls
        prefectures={page.stationOptions.prefectures}
        stations={page.stationOptions.stations}
        selectedPrecNo={page.selectedPrecNo}
        selectedStationId={page.selectedStationId}
        tempType={page.tempType}
        isLoadingPrefectures={page.stationOptionsLoadingPhase === 'prefectures'}
        isLoadingStations={page.stationOptionsLoadingPhase === 'stations'}
        onStationSelect={page.handleStationSelect}
        onPrefectureChange={page.handlePrefectureChange}
        onTempTypeChange={page.handleTempTypeChange}
      />
      <PrimaryLoadingStatus
        stationError={page.stationOptions.error?.message ?? null}
        stationLoadingPhase={page.stationOptionsLoadingPhase}
        temperatureError={page.temperatureError}
        activeOperation={page.activeOperation}
        progress={page.progress}
        onRetryStation={page.stationOptions.retry}
        onRetryTemperature={page.retryTemperature}
      />
      {page.selectedStationId !== null && page.startYear !== null && (
        <HeatmapViewport
          records={page.records}
          startYear={page.startYear}
          endYear={page.currentYear}
          tempType={page.tempType}
        />
      )}
      <LoadMoreStatus
        error={page.temperatureError}
        activeOperation={page.activeOperation}
        progress={page.progress}
        onRetry={page.retryTemperature}
      />
      {page.temperatureError === null &&
        page.activeOperation === null &&
        page.nextEndYear !== null &&
        page.startYear !== null &&
        page.hasOlderData && <LoadMoreButton nextEndYear={page.nextEndYear} onLoadMore={page.handleLoadMore} />}
      {page.selectedStationId !== null && page.startYear !== null && <ColorLegend />}
      <HeatmapFooter />
    </div>
  );
}
