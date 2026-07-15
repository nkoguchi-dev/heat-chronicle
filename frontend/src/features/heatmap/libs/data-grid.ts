import type { TemperatureRecord } from '@/features/heatmap/types/api';
import { parseCalendarDate } from '@/features/heatmap/libs/calendar-date';

export interface GridCell {
  date: string;
  maxTemp: number | null;
  minTemp: number | null;
  avgTemp: number | null;
}

// Map<year, Map<dayOfYear (0-based), GridCell>>
export type HeatmapGrid = Map<number, Map<number, GridCell>>;

export function buildGrid(records: TemperatureRecord[], startYear: number, endYear: number): HeatmapGrid {
  const grid: HeatmapGrid = new Map();

  // Initialize empty years
  for (let year = startYear; year <= endYear; year++) {
    grid.set(year, new Map());
  }

  for (const record of records) {
    const date = parseCalendarDate(record.date);
    if (!date) continue;

    const yearMap = grid.get(date.year);
    if (!yearMap) continue;

    yearMap.set(date.dayOfYear, {
      date: record.date,
      maxTemp: record.max_temp,
      minTemp: record.min_temp,
      avgTemp: record.avg_temp,
    });
  }

  return grid;
}

// Get the month label positions (day-of-year where each month starts)
export function getMonthStartDays(): { month: number; label: string; day: number }[] {
  // Using a non-leap year for consistent positions
  const months = [
    { month: 1, label: '1月', day: 0 },
    { month: 2, label: '2月', day: 31 },
    { month: 3, label: '3月', day: 59 },
    { month: 4, label: '4月', day: 90 },
    { month: 5, label: '5月', day: 120 },
    { month: 6, label: '6月', day: 151 },
    { month: 7, label: '7月', day: 181 },
    { month: 8, label: '8月', day: 212 },
    { month: 9, label: '9月', day: 243 },
    { month: 10, label: '10月', day: 273 },
    { month: 11, label: '11月', day: 304 },
    { month: 12, label: '12月', day: 334 },
  ];
  return months;
}
