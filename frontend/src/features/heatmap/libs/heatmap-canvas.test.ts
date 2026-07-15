import { describe, expect, it, vi } from 'vitest';

import { buildGrid } from '@/features/heatmap/libs/data-grid';
import {
  drawHeatmapGrid,
  getCellTemperature,
  getHeatmapDimensions,
  getHeatmapTooltip,
  LEFT_MARGIN,
  TOP_MARGIN,
} from '@/features/heatmap/libs/heatmap-canvas';
import type { TemperatureRecord } from '@/features/heatmap/types/api';

const RECORD: TemperatureRecord = {
  date: '2025-01-01',
  max_temp: 12.5,
  min_temp: null,
  avg_temp: 7,
};

describe('heatmap canvas helpers', () => {
  it('calculates dimensions and selects each temperature type', () => {
    const dimensions = getHeatmapDimensions(2024, 2025);
    const cell = buildGrid([RECORD], 2025, 2025).get(2025)?.get(0);

    expect(dimensions).toEqual({ width: 1148, height: 54, numberOfYears: 2 });
    expect(getCellTemperature(cell, 'max')).toBe(12.5);
    expect(getCellTemperature(cell, 'min')).toBeNull();
    expect(getCellTemperature(cell, 'avg')).toBe(7);
    expect(getCellTemperature(undefined, 'max')).toBeNull();
  });

  it('builds a tooltip for a populated cell and rejects points outside the grid', () => {
    const grid = buildGrid([RECORD], 2025, 2025);
    const dimensions = getHeatmapDimensions(2025, 2025);

    expect(getHeatmapTooltip(LEFT_MARGIN, TOP_MARGIN, grid, 2025, dimensions, 'max')).toEqual({
      x: LEFT_MARGIN + 10,
      y: TOP_MARGIN - 10,
      text: '2025年1月1日: 12.5℃',
      isRightAligned: false,
    });
    expect(getHeatmapTooltip(0, 0, grid, 2025, dimensions, 'max')).toBeNull();
    expect(getHeatmapTooltip(LEFT_MARGIN + 3, TOP_MARGIN, grid, 2025, dimensions, 'max')).toBeNull();
  });

  it('right-aligns tooltips and labels missing temperatures', () => {
    const farDayRecord = { ...RECORD, date: '2025-12-31' };
    const grid = buildGrid([farDayRecord], 2025, 2025);
    const dimensions = getHeatmapDimensions(2025, 2025);
    const horizontalPosition = LEFT_MARGIN + 364 * 3;

    expect(getHeatmapTooltip(horizontalPosition, TOP_MARGIN, grid, 2025, dimensions, 'min')).toMatchObject({
      text: '2025年12月31日: データなし',
      isRightAligned: true,
      x: horizontalPosition - 10,
    });
  });

  it('draws month labels, year labels, and daily cells', () => {
    const context = {
      fillStyle: '',
      font: '',
      textAlign: 'start',
      fillText: vi.fn(),
      fillRect: vi.fn(),
    } as unknown as CanvasRenderingContext2D;

    drawHeatmapGrid(context, buildGrid([RECORD], 2025, 2025), 2025, 1, 'max');

    expect(context.fillText).toHaveBeenCalledTimes(13);
    expect(context.fillRect).toHaveBeenCalledTimes(366);
  });
});
