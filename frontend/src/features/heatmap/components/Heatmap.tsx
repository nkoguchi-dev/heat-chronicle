'use client';

import { useCallback, useEffect, useMemo, useRef, useState } from 'react';

import { buildGrid } from '../libs/data-grid';
import { drawHeatmapGrid, getHeatmapDimensions, getHeatmapTooltip, type HeatmapTooltip } from '../libs/heatmap-canvas';
import type { TemperatureRecord, TempType } from '@/features/heatmap/types/api';

interface HeatmapProps {
  records: TemperatureRecord[];
  startYear: number;
  endYear: number;
  tempType: TempType;
}

export function Heatmap({ records, startYear, endYear, tempType }: HeatmapProps): React.JSX.Element {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const [tooltip, setTooltip] = useState<HeatmapTooltip | null>(null);

  const grid = useMemo(() => buildGrid(records, startYear, endYear), [records, startYear, endYear]);
  const dimensions = useMemo(() => getHeatmapDimensions(startYear, endYear), [startYear, endYear]);

  const drawHeatmap = useCallback((): void => {
    const canvas = canvasRef.current;
    if (!canvas) return;

    const devicePixelRatio = window.devicePixelRatio || 1;
    canvas.width = dimensions.width * devicePixelRatio;
    canvas.height = dimensions.height * devicePixelRatio;
    canvas.style.width = `${dimensions.width}px`;
    canvas.style.height = `${dimensions.height}px`;

    const context = canvas.getContext('2d');
    if (!context) return;
    context.scale(devicePixelRatio, devicePixelRatio);
    context.clearRect(0, 0, dimensions.width, dimensions.height);
    drawHeatmapGrid(context, grid, endYear, dimensions.numberOfYears, tempType);
  }, [dimensions, endYear, grid, tempType]);

  useEffect(() => {
    drawHeatmap();
  }, [drawHeatmap]);

  const handleMouseMove = useCallback(
    (event: React.MouseEvent<HTMLCanvasElement>): void => {
      const canvas = canvasRef.current;
      if (!canvas) return;

      const rect = canvas.getBoundingClientRect();
      const horizontalPosition = event.clientX - rect.left;
      const verticalPosition = event.clientY - rect.top;
      setTooltip(getHeatmapTooltip(horizontalPosition, verticalPosition, grid, endYear, dimensions, tempType));
    },
    [dimensions, endYear, grid, tempType],
  );

  const handleMouseLeave = useCallback((): void => {
    setTooltip(null);
  }, []);

  return (
    <div className="relative w-fit mx-auto">
      <canvas
        ref={canvasRef}
        onMouseMove={handleMouseMove}
        onMouseLeave={handleMouseLeave}
        className="cursor-crosshair"
      />
      {tooltip && (
        <div
          className="pointer-events-none absolute rounded bg-black/80 px-2 py-1 text-xs text-white whitespace-nowrap"
          style={
            tooltip.isRightAligned
              ? { right: dimensions.width - tooltip.x, top: tooltip.y }
              : { left: tooltip.x, top: tooltip.y }
          }
        >
          {tooltip.text}
        </div>
      )}
    </div>
  );
}
