import { describe, expect, it } from 'vitest';

import { getGradientStops, MAX_TEMPERATURE, MIN_TEMPERATURE, tempToColor } from '@/features/heatmap/libs/color-scale';

describe('tempToColor', () => {
  it('returns the missing-data color for null', () => {
    expect(tempToColor(null)).toBe('rgba(200, 200, 200, 0.3)');
  });

  it('clamps temperatures outside the supported range', () => {
    expect(tempToColor(MIN_TEMPERATURE - 1)).toBe('rgb(0,0,180)');
    expect(tempToColor(MAX_TEMPERATURE + 1)).toBe('rgb(180,0,0)');
  });

  it('interpolates between adjacent color stops', () => {
    expect(tempToColor(7.5)).toBe('rgb(178,203,203)');
  });
});

describe('getGradientStops', () => {
  it('returns offsets covering the full temperature range', () => {
    const stops = getGradientStops();

    expect(stops).toHaveLength(5);
    expect(stops[0]).toEqual({ offset: '0%', color: 'rgb(0,0,180)' });
    expect(stops.at(-1)).toEqual({ offset: '100%', color: 'rgb(180,0,0)' });
  });
});
