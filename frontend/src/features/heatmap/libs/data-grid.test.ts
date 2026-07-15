import { describe, expect, it } from 'vitest';

import { buildGrid, getMonthStartDays } from '@/features/heatmap/libs/data-grid';
import type { TemperatureRecord } from '@/features/heatmap/types/api';

const LEAP_DAY_RECORD: TemperatureRecord = {
  date: '2024-02-29',
  max_temp: 18,
  min_temp: 5,
  avg_temp: 11,
};

describe('buildGrid', () => {
  it('initializes every requested year and maps records to zero-based day indexes', () => {
    const grid = buildGrid([LEAP_DAY_RECORD], 2023, 2024);

    expect([...grid.keys()]).toEqual([2023, 2024]);
    expect(grid.get(2024)?.get(59)).toEqual({
      date: '2024-02-29',
      maxTemp: 18,
      minTemp: 5,
      avgTemp: 11,
    });
  });

  it('ignores records outside the requested year range', () => {
    const grid = buildGrid([LEAP_DAY_RECORD], 2023, 2023);

    expect(grid.get(2023)?.size).toBe(0);
  });
});

describe('getMonthStartDays', () => {
  it('returns stable non-leap-year positions for all months', () => {
    const months = getMonthStartDays();

    expect(months).toHaveLength(12);
    expect(months[0]).toEqual({ month: 1, label: '1月', day: 0 });
    expect(months.at(-1)).toEqual({ month: 12, label: '12月', day: 334 });
  });
});
