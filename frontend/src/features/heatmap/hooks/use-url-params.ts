import { useCallback, useEffect, useMemo, useSyncExternalStore } from 'react';

import { applyUrlParams, parseUrlParams, type UrlParams } from '@/features/heatmap/libs/url-params';

interface UseUrlParamsReturn {
  params: UrlParams;
  updateUrl: (params: Partial<UrlParams>, mode?: UrlUpdateMode) => void;
}

export type UrlUpdateMode = 'push' | 'replace';

const URL_CHANGE_EVENT = 'heat-chronicle:url-change';
const SERVER_SEARCH_SNAPSHOT = '';

function subscribeToUrlChanges(onStoreChange: () => void): () => void {
  window.addEventListener('popstate', onStoreChange);
  window.addEventListener(URL_CHANGE_EVENT, onStoreChange);

  return () => {
    window.removeEventListener('popstate', onStoreChange);
    window.removeEventListener(URL_CHANGE_EVENT, onStoreChange);
  };
}

function getBrowserSearchSnapshot(): string {
  return window.location.search;
}

function getServerSearchSnapshot(): string {
  return SERVER_SEARCH_SNAPSHOT;
}

function writeUrl(params: Partial<UrlParams>, mode: UrlUpdateMode): void {
  const nextUrl = applyUrlParams(new URL(window.location.href), params);
  const nextPath = `${nextUrl.pathname}${nextUrl.search}${nextUrl.hash}`;

  if (mode === 'push') window.history.pushState(null, '', nextPath);
  else window.history.replaceState(null, '', nextPath);

  window.dispatchEvent(new Event(URL_CHANGE_EVENT));
}

export function useUrlParams(): UseUrlParamsReturn {
  const search = useSyncExternalStore(subscribeToUrlChanges, getBrowserSearchSnapshot, getServerSearchSnapshot);
  const parsed = useMemo(() => parseUrlParams(search), [search]);
  const updateUrl = useCallback((params: Partial<UrlParams>, mode: UrlUpdateMode = 'push'): void => {
    writeUrl(params, mode);
  }, []);

  useEffect(() => {
    const browserParsed = parseUrlParams(window.location.search);
    if (browserParsed.needsNormalization) updateUrl(browserParsed.params, 'replace');
  }, [search, updateUrl]);

  return { params: parsed.params, updateUrl };
}
