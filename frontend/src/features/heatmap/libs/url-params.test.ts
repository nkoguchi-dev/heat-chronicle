import { describe, expect, it } from 'vitest';

import {
  applyUrlParams,
  DEFAULT_PREFECTURE_NUMBER,
  DEFAULT_STATION_ID,
  isTempType,
  parseUrlParams,
} from '@/features/heatmap/libs/url-params';

describe('parseUrlParams', () => {
  it('parses valid station, prefecture, and temperature type values', () => {
    expect(parseUrlParams('?pref=13&station=47662&type=avg')).toEqual({
      params: { pref: 13, station: 47662, type: 'avg' },
      usesDefaults: false,
    });
  });

  it('uses defaults when neither location value is valid', () => {
    expect(parseUrlParams('?pref=x&station=-1&type=unknown')).toEqual({
      params: {
        pref: DEFAULT_PREFECTURE_NUMBER,
        station: DEFAULT_STATION_ID,
        type: 'max',
      },
      usesDefaults: true,
    });
  });

  it('rejects zero and integers outside the safe range', () => {
    expect(parseUrlParams('?pref=0&station=999999999999999999999')).toMatchObject({
      usesDefaults: true,
    });
  });

  it('preserves a valid partial location without applying defaults', () => {
    expect(parseUrlParams('?pref=1')).toEqual({
      params: { pref: 1, station: null, type: 'max' },
      usesDefaults: false,
    });
  });
});

describe('applyUrlParams', () => {
  it('sets and deletes location and non-default type parameters', () => {
    const originalUrl = new URL('https://example.com/?pref=44&station=4&type=min&other=value');
    const nextUrl = applyUrlParams(originalUrl, { pref: 13, station: null, type: 'max' });

    expect(nextUrl.searchParams.get('pref')).toBe('13');
    expect(nextUrl.searchParams.has('station')).toBe(false);
    expect(nextUrl.searchParams.has('type')).toBe(false);
    expect(nextUrl.searchParams.get('other')).toBe('value');
    expect(originalUrl.searchParams.get('station')).toBe('4');
  });

  it('deletes a prefecture and sets station and non-default type values', () => {
    const nextUrl = applyUrlParams(new URL('https://example.com/?pref=44'), {
      pref: null,
      station: 10,
      type: 'min',
    });

    expect(nextUrl.search).toBe('?station=10&type=min');
  });
});

describe('isTempType', () => {
  it('narrows supported values only', () => {
    expect(isTempType('max')).toBe(true);
    expect(isTempType('min')).toBe(true);
    expect(isTempType('avg')).toBe(true);
    expect(isTempType('median')).toBe(false);
    expect(isTempType(null)).toBe(false);
  });
});
