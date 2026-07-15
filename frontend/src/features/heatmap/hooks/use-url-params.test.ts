import { act, renderHook } from '@testing-library/react';
import { beforeEach, describe, expect, it, vi } from 'vitest';

import { useUrlParams } from '@/features/heatmap/hooks/use-url-params';

beforeEach(() => {
  window.history.replaceState(null, '', '/');
});

describe('useUrlParams', () => {
  it('applies and writes the default location when no location is present', () => {
    const replaceState = vi.spyOn(window.history, 'replaceState');

    const { result } = renderHook(() => useUrlParams());

    expect(result.current.initialParams).toEqual({ pref: 44, station: 4, type: 'max' });
    expect(replaceState).toHaveBeenCalled();
    expect(window.location.search).toBe('?pref=44&station=4');
  });

  it('updates only the requested URL values', () => {
    window.history.replaceState(null, '', '/?pref=13&station=1&type=min');
    const { result } = renderHook(() => useUrlParams());

    act(() => result.current.updateUrl({ station: 2, type: 'avg' }));

    expect(window.location.search).toBe('?pref=13&station=2&type=avg');
  });
});
