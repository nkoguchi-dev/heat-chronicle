import { afterEach, describe, expect, it } from 'vitest';

import { formatJapaneseCalendarDate, parseCalendarDate } from '@/features/heatmap/libs/calendar-date';

const originalTimeZone = process.env.TZ;

afterEach(() => {
  if (originalTimeZone === undefined) {
    delete process.env.TZ;
  } else {
    process.env.TZ = originalTimeZone;
  }
});

describe('parseCalendarDate', () => {
  it('parses a leap day independently of the process time zone', () => {
    process.env.TZ = 'America/Los_Angeles';

    expect(parseCalendarDate('2024-02-29')).toEqual({
      year: 2024,
      month: 2,
      day: 29,
      dayOfYear: 59,
    });
  });

  it.each(['2025-02-29', '2025-13-01', '2025-01-00', 'not-a-date'])('rejects invalid calendar date %s', (value) => {
    expect(parseCalendarDate(value)).toBeNull();
  });
});

describe('formatJapaneseCalendarDate', () => {
  it('formats a calendar date without local-time conversion', () => {
    process.env.TZ = 'America/Los_Angeles';

    expect(formatJapaneseCalendarDate('2025-01-01')).toBe('2025年1月1日');
  });

  it('preserves an invalid value for a safe fallback', () => {
    expect(formatJapaneseCalendarDate('unknown')).toBe('unknown');
  });
});
