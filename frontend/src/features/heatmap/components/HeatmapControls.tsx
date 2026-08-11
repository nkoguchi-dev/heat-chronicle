import { StationSelector } from './StationSelector';
import { TemperatureTypeSelector } from './TemperatureTypeSelector';

import type { Prefecture, Station, TempType } from '../types/api';

interface HeatmapControlsProps {
  prefectures: Prefecture[];
  stations: Station[];
  selectedPrecNo: number | null;
  selectedStationId: number | null;
  tempType: TempType;
  isLoadingPrefectures: boolean;
  isLoadingStations: boolean;
  onStationSelect: (station: Station) => void;
  onPrefectureChange: (precNo: number) => void;
  onTempTypeChange: (value: string) => void;
}

export function HeatmapControls(props: HeatmapControlsProps): React.JSX.Element {
  return (
    <div className="flex w-full max-w-md flex-col items-stretch gap-3 md:w-auto md:max-w-none md:flex-row md:items-center md:gap-4">
      <StationSelector
        prefectures={props.prefectures}
        stations={props.stations}
        selectedPrecNo={props.selectedPrecNo}
        selectedStationId={props.selectedStationId}
        isLoadingPrefectures={props.isLoadingPrefectures}
        isLoadingStations={props.isLoadingStations}
        onSelect={props.onStationSelect}
        onPrefectureChange={props.onPrefectureChange}
      />
      <TemperatureTypeSelector value={props.tempType} onChange={props.onTempTypeChange} />
    </div>
  );
}
