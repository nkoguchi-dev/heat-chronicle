import type { TemperatureRecord } from '@/features/heatmap/types/api';
import type { TemperatureLoadOperation } from '@/features/heatmap/types/temperature-data';

export interface TemperatureMonth {
  year: number;
  month: number;
}

export function buildMonthsToFetch(
  startYear: number,
  endYear: number,
  fetchedMonths: string[],
  currentDate: Date = new Date(),
): TemperatureMonth[] {
  const fetchedMonthSet = new Set(fetchedMonths);
  const months: TemperatureMonth[] = [];
  const currentYear = currentDate.getFullYear();
  const currentMonth = currentDate.getMonth() + 1;

  for (let year = endYear; year >= startYear; year--) {
    for (let month = 12; month >= 1; month--) {
      const isFutureMonth = year > currentYear || (year === currentYear && month > currentMonth);
      if (isFutureMonth) continue;

      const monthKey = `${year}-${String(month).padStart(2, '0')}`;
      if (!fetchedMonthSet.has(monthKey)) months.push({ year, month });
    }
  }

  return months;
}

export function mergeTemperatureRecords(
  currentRecords: TemperatureRecord[],
  incomingRecords: TemperatureRecord[],
): TemperatureRecord[] {
  if (incomingRecords.length === 0) return currentRecords;

  const mergedRecords = [...currentRecords];
  const indexByDate = new Map(currentRecords.map((record, index) => [record.date, index]));

  for (const record of incomingRecords) {
    const existingIndex = indexByDate.get(record.date);
    if (existingIndex === undefined) {
      indexByDate.set(record.date, mergedRecords.length);
      mergedRecords.push(record);
    } else {
      mergedRecords[existingIndex] = record;
    }
  }

  return mergedRecords;
}

export function getTemperatureLoadErrorMessage(
  operation: TemperatureLoadOperation,
  hasPartialFailure: boolean,
): string {
  if (hasPartialFailure) return '一部の月の気温データを取得できませんでした。';
  if (operation.mode === 'more') return `〜${operation.endYear}年の気温データを取得できませんでした。`;
  return '気温データを取得できませんでした。';
}
