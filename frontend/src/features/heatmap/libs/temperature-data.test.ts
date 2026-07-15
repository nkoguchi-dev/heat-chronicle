import { describe, expect, it } from 'vitest';

import {
  buildMonthsToFetch,
  getTemperatureLoadErrorMessage,
  mergeTemperatureRecords,
} from '@/features/heatmap/libs/temperature-data';
import type { TemperatureRecord } from '@/features/heatmap/types/api';

const EXISTING_RECORD: TemperatureRecord = {
  date: '2025-01-01',
  max_temp: 10,
  min_temp: 1,
  avg_temp: 5,
};

describe('buildMonthsToFetch', () => {
  it('returns unfetched months newest-first and excludes future months', () => {
    expect(buildMonthsToFetch(2025, 2026, ['2025-12'], new Date('2026-02-15T00:00:00Z'))).toEqual([
      { year: 2026, month: 2 },
      { year: 2026, month: 1 },
      ...Array.from({ length: 11 }, (_, index) => ({ year: 2025, month: 11 - index })),
    ]);
  });
});

describe('mergeTemperatureRecords', () => {
  it('keeps the original array when there is nothing to merge', () => {
    expect(mergeTemperatureRecords([EXISTING_RECORD], [])).toBeDefined();
    expect(mergeTemperatureRecords([EXISTING_RECORD], [])[0]).toBe(EXISTING_RECORD);
  });

  it('replaces duplicate dates and appends new dates', () => {
    const replacement = { ...EXISTING_RECORD, max_temp: 20 };
    const appended = { ...EXISTING_RECORD, date: '2025-01-02' };

    expect(mergeTemperatureRecords([EXISTING_RECORD], [replacement, appended])).toEqual([replacement, appended]);
  });
});

describe('getTemperatureLoadErrorMessage', () => {
  it('returns messages for partial, initial, and historical failures', () => {
    const initialOperation = { mode: 'initial' as const, stationId: 4, endYear: 2026 };
    const moreOperation = { mode: 'more' as const, stationId: 4, endYear: 2016 };

    expect(getTemperatureLoadErrorMessage(initialOperation, true)).toContain('一部の月');
    expect(getTemperatureLoadErrorMessage(initialOperation, false)).toBe('気温データを取得できませんでした。');
    expect(getTemperatureLoadErrorMessage(moreOperation, false)).toContain('2016年');
  });
});
