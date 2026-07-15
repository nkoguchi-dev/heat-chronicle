import { useMemo } from 'react';

import {
  DEFAULT_PREFECTURE_NUMBER,
  DEFAULT_STATION_ID,
  applyUrlParams,
  parseUrlParams,
  type UrlParams,
} from '@/features/heatmap/libs/url-params';

interface UseUrlParamsReturn {
  initialParams: UrlParams;
  updateUrl: (params: Partial<UrlParams>) => void;
}

function parseParams(): UrlParams {
  if (typeof window === 'undefined') {
    return { station: DEFAULT_STATION_ID, pref: DEFAULT_PREFECTURE_NUMBER, type: 'max' };
  }

  const parsed = parseUrlParams(window.location.search);
  if (parsed.usesDefaults) {
    const defaultUrl = applyUrlParams(new URL(window.location.href), parsed.params);
    window.history.replaceState(null, '', defaultUrl.toString());
  }

  return parsed.params;
}

function updateUrl(params: Partial<UrlParams>): void {
  const nextUrl = applyUrlParams(new URL(window.location.href), params);
  window.history.replaceState(null, '', nextUrl.toString());
}

export function useUrlParams(): UseUrlParamsReturn {
  const initialParams = useMemo(() => parseParams(), []);

  return { initialParams, updateUrl };
}
