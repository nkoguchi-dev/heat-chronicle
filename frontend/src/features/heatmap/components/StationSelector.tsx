'use client';

import { memo } from 'react';

import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import type { Prefecture, Station } from '@/features/heatmap/types/api';

interface StationSelectorProps {
  prefectures: Prefecture[];
  stations: Station[];
  selectedPrecNo: number | null;
  selectedStationId: number | null;
  isLoadingPrefectures: boolean;
  isLoadingStations: boolean;
  onPrefectureChange: (precNo: number) => void;
  onSelect: (station: Station) => void;
}

function StationSelectorInner({
  prefectures,
  stations,
  selectedPrecNo,
  selectedStationId,
  isLoadingPrefectures,
  isLoadingStations,
  onPrefectureChange,
  onSelect,
}: StationSelectorProps): React.JSX.Element {
  const hasSelectedPrefecture = prefectures.some((prefecture) => prefecture.prec_no === selectedPrecNo);
  const hasSelectedStation = stations.some((station) => station.id === selectedStationId);

  return (
    <div className="flex flex-col gap-2 md:flex-row md:items-center">
      <Select
        value={hasSelectedPrefecture ? (selectedPrecNo?.toString() ?? '') : ''}
        onValueChange={(value) => onPrefectureChange(Number(value))}
        disabled={isLoadingPrefectures || prefectures.length === 0}
      >
        <SelectTrigger className="w-full md:w-[180px]" aria-busy={isLoadingPrefectures}>
          <SelectValue placeholder={isLoadingPrefectures ? '読み込み中...' : '都道府県を選択'} />
        </SelectTrigger>
        <SelectContent>
          {prefectures.map((prefecture) => (
            <SelectItem key={prefecture.prec_no} value={prefecture.prec_no.toString()}>
              {prefecture.name}
            </SelectItem>
          ))}
        </SelectContent>
      </Select>

      <Select
        value={hasSelectedStation ? (selectedStationId?.toString() ?? '') : ''}
        onValueChange={(value) => {
          const station = stations.find((candidate) => candidate.id === Number(value));
          if (station) onSelect(station);
        }}
        disabled={selectedPrecNo === null || isLoadingPrefectures || isLoadingStations || stations.length === 0}
      >
        <SelectTrigger className="w-full md:w-[180px]" aria-busy={isLoadingStations}>
          <SelectValue placeholder={isLoadingStations ? '読み込み中...' : '地点を選択'} />
        </SelectTrigger>
        <SelectContent>
          {stations.map((station) => (
            <SelectItem key={station.id} value={station.id.toString()}>
              {station.station_name}
            </SelectItem>
          ))}
        </SelectContent>
      </Select>
    </div>
  );
}

export const StationSelector = memo(StationSelectorInner);
