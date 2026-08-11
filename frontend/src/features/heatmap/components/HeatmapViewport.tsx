import { Heatmap } from './Heatmap';

import type { TemperatureRecord, TempType } from '../types/api';

interface HeatmapViewportProps {
  records: TemperatureRecord[];
  startYear: number;
  endYear: number;
  tempType: TempType;
}

export function HeatmapViewport({ records, startYear, endYear, tempType }: HeatmapViewportProps): React.JSX.Element {
  return (
    <div className="w-full">
      <p id="heatmap-scroll-hint" className="mb-2 text-center text-xs text-muted-foreground md:hidden">
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
        <Heatmap records={records} startYear={startYear} endYear={endYear} tempType={tempType} />
      </div>
    </div>
  );
}
