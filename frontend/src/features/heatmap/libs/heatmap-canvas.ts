import { tempToColor } from '@/features/heatmap/libs/color-scale';
import { getMonthStartDays, type GridCell, type HeatmapGrid } from '@/features/heatmap/libs/data-grid';
import type { TempType } from '@/features/heatmap/types/api';

export const CELL_WIDTH = 3;
export const CELL_HEIGHT = 12;
export const LEFT_MARGIN = 50;
export const TOP_MARGIN = 30;
export const DAYS_PER_YEAR = 366;

export interface HeatmapDimensions {
  width: number;
  height: number;
  numberOfYears: number;
}

export interface HeatmapTooltip {
  x: number;
  y: number;
  text: string;
  isRightAligned: boolean;
}

export function getCellTemperature(cell: GridCell | undefined, temperatureType: TempType): number | null {
  if (!cell) return null;
  if (temperatureType === 'max') return cell.maxTemp;
  if (temperatureType === 'min') return cell.minTemp;
  return cell.avgTemp;
}

export function getHeatmapDimensions(startYear: number, endYear: number): HeatmapDimensions {
  const numberOfYears = endYear - startYear + 1;
  return {
    width: LEFT_MARGIN + DAYS_PER_YEAR * CELL_WIDTH,
    height: TOP_MARGIN + numberOfYears * CELL_HEIGHT,
    numberOfYears,
  };
}

export function drawHeatmapGrid(
  context: CanvasRenderingContext2D,
  grid: HeatmapGrid,
  endYear: number,
  numberOfYears: number,
  temperatureType: TempType,
): void {
  context.fillStyle = '#666';
  context.font = '11px sans-serif';
  context.textAlign = 'center';
  for (const { label, day } of getMonthStartDays()) {
    context.fillText(label, LEFT_MARGIN + day * CELL_WIDTH + 12, TOP_MARGIN - 8);
  }

  for (let yearIndex = 0; yearIndex < numberOfYears; yearIndex++) {
    const year = endYear - yearIndex;
    const verticalPosition = TOP_MARGIN + yearIndex * CELL_HEIGHT;
    context.fillStyle = '#666';
    context.font = '10px sans-serif';
    context.textAlign = 'right';
    context.fillText(String(year), LEFT_MARGIN - 6, verticalPosition + CELL_HEIGHT - 2);

    const yearData = grid.get(year);
    for (let dayIndex = 0; dayIndex < DAYS_PER_YEAR; dayIndex++) {
      const cell = yearData?.get(dayIndex);
      const horizontalPosition = LEFT_MARGIN + dayIndex * CELL_WIDTH;
      context.fillStyle = tempToColor(getCellTemperature(cell, temperatureType));
      context.fillRect(horizontalPosition, verticalPosition, CELL_WIDTH, CELL_HEIGHT);
    }
  }
}

export function getHeatmapTooltip(
  horizontalPosition: number,
  verticalPosition: number,
  grid: HeatmapGrid,
  endYear: number,
  dimensions: HeatmapDimensions,
  temperatureType: TempType,
): HeatmapTooltip | null {
  const dayIndex = Math.floor((horizontalPosition - LEFT_MARGIN) / CELL_WIDTH);
  const yearIndex = Math.floor((verticalPosition - TOP_MARGIN) / CELL_HEIGHT);
  const isOutsideGrid =
    dayIndex < 0 || dayIndex >= DAYS_PER_YEAR || yearIndex < 0 || yearIndex >= dimensions.numberOfYears;
  if (isOutsideGrid) return null;

  const cell = grid.get(endYear - yearIndex)?.get(dayIndex);
  if (!cell) return null;

  const date = new Date(cell.date);
  const dateLabel = `${date.getFullYear()}年${date.getMonth() + 1}月${date.getDate()}日`;
  const temperature = getCellTemperature(cell, temperatureType);
  const temperatureLabel = temperature === null ? 'データなし' : `${temperature.toFixed(1)}℃`;
  const isRightAligned = horizontalPosition > dimensions.width / 2;

  return {
    x: isRightAligned ? horizontalPosition - 10 : horizontalPosition + 10,
    y: verticalPosition - 10,
    text: `${dateLabel}: ${temperatureLabel}`,
    isRightAligned,
  };
}
