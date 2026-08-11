import { act, renderHook, screen, waitFor } from '@testing-library/react';
import { createElement } from 'react';
import { hydrateRoot, type Root } from 'react-dom/client';
import { renderToString } from 'react-dom/server';
import { beforeEach, describe, expect, it, vi } from 'vitest';

import { useUrlParams } from '@/features/heatmap/hooks/use-url-params';

beforeEach(() => {
  window.history.replaceState(null, '', '/');
});

describe('useUrlParams', () => {
  it('applies and writes the default location when no location is present', async () => {
    const replaceState = vi.spyOn(window.history, 'replaceState');

    const { result } = renderHook(() => useUrlParams());

    expect(result.current.params).toEqual({ pref: 44, station: 4, type: 'max' });
    await waitFor(() => expect(window.location.search).toBe('?pref=44&station=4'));
    expect(replaceState).toHaveBeenCalledOnce();
  });

  it('pushes only the requested URL values by default', () => {
    window.history.replaceState(null, '', '/?pref=13&station=1&type=min');
    const pushState = vi.spyOn(window.history, 'pushState');
    const { result } = renderHook(() => useUrlParams());

    act(() => result.current.updateUrl({ station: 2, type: 'avg' }));

    expect(window.location.search).toBe('?pref=13&station=2&type=avg');
    expect(result.current.params).toEqual({ pref: 13, station: 2, type: 'avg' });
    expect(pushState).toHaveBeenCalledOnce();
  });

  it('replaces the current entry when requested', () => {
    window.history.replaceState(null, '', '/?pref=13');
    const replaceState = vi.spyOn(window.history, 'replaceState');
    const pushState = vi.spyOn(window.history, 'pushState');
    const { result } = renderHook(() => useUrlParams());

    act(() => result.current.updateUrl({ station: 1 }, 'replace'));

    expect(window.location.search).toBe('?pref=13&station=1');
    expect(replaceState).toHaveBeenCalledOnce();
    expect(pushState).not.toHaveBeenCalled();
  });

  it('reads the current URL after a popstate event', () => {
    window.history.replaceState(null, '', '/?pref=44&station=4');
    const { result } = renderHook(() => useUrlParams());

    act(() => {
      window.history.replaceState(null, '', '/?pref=13&station=1&type=min');
      window.dispatchEvent(new PopStateEvent('popstate'));
    });

    expect(result.current.params).toEqual({ pref: 13, station: 1, type: 'min' });
  });

  it('hydrates with the server snapshot before restoring a non-default temperature type', async () => {
    window.history.replaceState(null, '', '/?pref=44&station=4&type=min');

    function ParamsView(): React.ReactElement {
      const { params } = useUrlParams();
      return createElement('p', null, params.type);
    }

    const container = document.createElement('div');
    container.innerHTML = renderToString(createElement(ParamsView));
    document.body.append(container);
    expect(container).toHaveTextContent('max');
    const consoleError = vi.spyOn(console, 'error').mockImplementation(() => undefined);
    let root: Root;

    await act(async () => {
      root = hydrateRoot(container, createElement(ParamsView));
    });

    await waitFor(() => expect(screen.getByText('min')).toBeInTheDocument());
    const hydrationErrors = consoleError.mock.calls.filter(([message]) => String(message).match(/hydration|#418/i));
    expect(hydrationErrors).toEqual([]);

    act(() => root.unmount());
    container.remove();
  });
});
