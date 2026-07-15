const CALENDAR_DATE_PATTERN = /^(\d{4})-(\d{2})-(\d{2})$/;
const MILLISECONDS_PER_DAY = 24 * 60 * 60 * 1000;

export interface CalendarDate {
  year: number;
  month: number;
  day: number;
  dayOfYear: number;
}

export function parseCalendarDate(value: string): CalendarDate | null {
  const match = CALENDAR_DATE_PATTERN.exec(value);
  if (!match) return null;

  const year = Number(match[1]);
  const month = Number(match[2]);
  const day = Number(match[3]);
  const timestamp = Date.UTC(year, month - 1, day);
  const date = new Date(timestamp);
  const isValidDate = date.getUTCFullYear() === year && date.getUTCMonth() === month - 1 && date.getUTCDate() === day;
  if (!isValidDate) return null;

  const startOfYear = Date.UTC(year, 0, 1);
  return {
    year,
    month,
    day,
    dayOfYear: Math.floor((timestamp - startOfYear) / MILLISECONDS_PER_DAY),
  };
}

export function formatJapaneseCalendarDate(value: string): string {
  const date = parseCalendarDate(value);
  return date ? `${date.year}年${date.month}月${date.day}日` : value;
}
