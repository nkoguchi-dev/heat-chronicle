import type { TemperatureRecord } from "@/types/api";

export interface GridCell {
  date: string;
  maxTemp: number | null;
  minTemp: number | null;
  avgTemp: number | null;
}

// Map<year, Map<dayOfYear (0-based), GridCell>>
export type HeatmapGrid = Map<number, Map<number, GridCell>>;

function dayOfYear(dateStr: string): number {
  const d = new Date(dateStr);
  const start = new Date(d.getFullYear(), 0, 0);
  const diff = d.getTime() - start.getTime();
  return Math.floor(diff / (1000 * 60 * 60 * 24)) - 1; // 0-based
}

export function buildGrid(
  records: TemperatureRecord[],
  startYear: number,
  endYear: number
): HeatmapGrid {
  const grid: HeatmapGrid = new Map();

  // Initialize empty years
  for (let y = startYear; y <= endYear; y++) {
    grid.set(y, new Map());
  }

  for (const record of records) {
    const year = parseInt(record.date.substring(0, 4), 10);
    const yearMap = grid.get(year);
    if (!yearMap) continue;

    const doy = dayOfYear(record.date);
    yearMap.set(doy, {
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
    { month: 1, label: "1月", day: 0 },
    { month: 2, label: "2月", day: 31 },
    { month: 3, label: "3月", day: 59 },
    { month: 4, label: "4月", day: 90 },
    { month: 5, label: "5月", day: 120 },
    { month: 6, label: "6月", day: 151 },
    { month: 7, label: "7月", day: 181 },
    { month: 8, label: "8月", day: 212 },
    { month: 9, label: "9月", day: 243 },
    { month: 10, label: "10月", day: 273 },
    { month: 11, label: "11月", day: 304 },
    { month: 12, label: "12月", day: 334 },
  ];
  return months;
}
