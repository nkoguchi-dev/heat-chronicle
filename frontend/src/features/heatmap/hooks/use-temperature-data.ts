'use client';

import { useCallback, useEffect, useRef, useState } from 'react';

import { apiClient } from '@/features/shared/libs/api-client';
import {
  buildMonthsToFetch,
  getTemperatureLoadErrorMessage,
  mergeTemperatureRecords,
  type TemperatureMonth,
} from '@/features/heatmap/libs/temperature-data';
import type {
  MonthTemperatureResponse,
  ProgressEvent,
  TemperatureRecord,
  TemperatureResponse,
} from '@/features/heatmap/types/api';
import type { TemperatureLoadError, TemperatureLoadOperation } from '@/features/heatmap/types/temperature-data';

export type { TemperatureLoadError, TemperatureLoadOperation } from '@/features/heatmap/types/temperature-data';

const REQUEST_INTERVAL_MS = 2000;

interface UseTemperatureDataReturn {
  records: TemperatureRecord[];
  activeOperation: TemperatureLoadOperation | null;
  progress: ProgressEvent | null;
  error: TemperatureLoadError | null;
  hasOlderData: boolean;
  nextEndYear: number | null;
  startYear: number | null;
  fetchData: (stationId: number, endYear: number) => void;
  fetchMoreData: (stationId: number, endYear: number) => void;
  retry: () => void;
  reset: () => void;
}

function isAbortError(error: unknown): boolean {
  return error instanceof DOMException && error.name === 'AbortError';
}

async function waitForNextRequest(signal: AbortSignal): Promise<void> {
  await new Promise<void>((resolve, reject) => {
    const handleAbort = (): void => {
      clearTimeout(timer);
      reject(new DOMException('Aborted', 'AbortError'));
    };
    const timer = setTimeout(() => {
      signal.removeEventListener('abort', handleAbort);
      resolve();
    }, REQUEST_INTERVAL_MS);
    signal.addEventListener('abort', handleAbort, { once: true });
  });
}

async function fetchMissingMonths(
  stationId: number,
  months: TemperatureMonth[],
  controller: AbortController,
  fetchId: number,
  fetchIdRef: React.RefObject<number>,
  setRecords: React.Dispatch<React.SetStateAction<TemperatureRecord[]>>,
  setProgress: React.Dispatch<React.SetStateAction<ProgressEvent | null>>,
): Promise<number> {
  const total = months.length;
  let failedCount = 0;

  for (let monthIndex = 0; monthIndex < months.length; monthIndex++) {
    if (fetchIdRef.current !== fetchId || controller.signal.aborted) break;

    const { year, month } = months[monthIndex];
    setProgress({ year, month, completed: monthIndex, total });

    try {
      const monthData = await apiClient.get<MonthTemperatureResponse>(
        `/api/temperature/${stationId}/fetch-month?year=${year}&month=${month}`,
        { signal: controller.signal },
      );

      if (fetchIdRef.current !== fetchId) break;

      setRecords((current) => mergeTemperatureRecords(current, monthData.records));
      setProgress({ year, month, completed: monthIndex + 1, total });
    } catch (requestError) {
      if (isAbortError(requestError)) break;
      failedCount += 1;
      console.error(`Failed to fetch ${year}-${month}:`, requestError);
    }

    if (monthIndex < months.length - 1 && !controller.signal.aborted) {
      try {
        await waitForNextRequest(controller.signal);
      } catch (requestError) {
        if (isAbortError(requestError)) break;
        throw requestError;
      }
    }
  }

  return failedCount;
}

export function useTemperatureData(): UseTemperatureDataReturn {
  const [records, setRecords] = useState<TemperatureRecord[]>([]);
  const [activeOperation, setActiveOperation] = useState<TemperatureLoadOperation | null>(null);
  const [progress, setProgress] = useState<ProgressEvent | null>(null);
  const [error, setError] = useState<TemperatureLoadError | null>(null);
  const [hasOlderData, setHasOlderData] = useState(false);
  const [nextEndYear, setNextEndYear] = useState<number | null>(null);
  const [startYear, setStartYear] = useState<number | null>(null);

  const fetchIdRef = useRef(0);
  const abortControllerRef = useRef<AbortController | null>(null);
  const activeOperationRef = useRef<TemperatureLoadOperation | null>(null);
  const failedOperationRef = useRef<TemperatureLoadOperation | null>(null);

  const finishOperation = useCallback((operation: TemperatureLoadOperation, fetchId: number): void => {
    if (fetchIdRef.current !== fetchId) return;
    if (activeOperationRef.current === operation) {
      activeOperationRef.current = null;
    }
    abortControllerRef.current = null;
    setActiveOperation(null);
    setProgress(null);
  }, []);

  const executeOperation = useCallback(
    (operation: TemperatureLoadOperation): void => {
      abortControllerRef.current?.abort();
      const controller = new AbortController();
      abortControllerRef.current = controller;
      const fetchId = ++fetchIdRef.current;

      activeOperationRef.current = operation;
      failedOperationRef.current = null;
      setActiveOperation(operation);
      setProgress(null);
      setError(null);

      if (operation.mode === 'initial') {
        setRecords([]);
        setHasOlderData(false);
        setNextEndYear(null);
        setStartYear(null);
      }

      void apiClient
        .get<TemperatureResponse>(`/api/temperature/${operation.stationId}?end_year=${operation.endYear}`, {
          signal: controller.signal,
        })
        .then(async (response) => {
          if (fetchIdRef.current !== fetchId) return;

          if (operation.mode === 'initial') {
            setRecords(response.data);
          } else {
            setRecords((current) => mergeTemperatureRecords(current, response.data));
          }
          setStartYear(response.metadata.start_year);
          setHasOlderData(response.metadata.has_older_data);
          setNextEndYear(response.metadata.next_end_year);

          let failedCount = 0;
          if (response.metadata.fetching_required) {
            const months = buildMonthsToFetch(
              response.metadata.start_year,
              operation.endYear,
              response.metadata.fetched_months,
            );
            failedCount = await fetchMissingMonths(
              operation.stationId,
              months,
              controller,
              fetchId,
              fetchIdRef,
              setRecords,
              setProgress,
            );
          }

          if (fetchIdRef.current !== fetchId || controller.signal.aborted) {
            return;
          }

          if (failedCount > 0) {
            failedOperationRef.current = operation;
            setError({
              operation,
              message: getTemperatureLoadErrorMessage(operation, true),
            });
          }

          finishOperation(operation, fetchId);
        })
        .catch((requestError) => {
          if (isAbortError(requestError)) return;
          console.error('Failed to fetch temperature data:', requestError);
          if (fetchIdRef.current === fetchId) {
            failedOperationRef.current = operation;
            setError({
              operation,
              message: getTemperatureLoadErrorMessage(operation, false),
            });
            finishOperation(operation, fetchId);
          }
        });
    },
    [finishOperation],
  );

  const fetchData = useCallback(
    (stationId: number, endYear: number): void => {
      executeOperation({ mode: 'initial', stationId, endYear });
    },
    [executeOperation],
  );

  const fetchMoreData = useCallback(
    (stationId: number, endYear: number): void => {
      if (activeOperationRef.current !== null || failedOperationRef.current !== null) {
        return;
      }
      executeOperation({ mode: 'more', stationId, endYear });
    },
    [executeOperation],
  );

  const retry = useCallback((): void => {
    const operation = failedOperationRef.current;
    if (operation) {
      executeOperation(operation);
    }
  }, [executeOperation]);

  const reset = useCallback((): void => {
    abortControllerRef.current?.abort();
    abortControllerRef.current = null;
    ++fetchIdRef.current;
    activeOperationRef.current = null;
    failedOperationRef.current = null;
    setRecords([]);
    setActiveOperation(null);
    setProgress(null);
    setError(null);
    setHasOlderData(false);
    setNextEndYear(null);
    setStartYear(null);
  }, []);

  useEffect(
    () => () => {
      abortControllerRef.current?.abort();
    },
    [],
  );

  return {
    records,
    activeOperation,
    progress,
    error,
    hasOlderData,
    nextEndYear,
    startYear,
    fetchData,
    fetchMoreData,
    retry,
    reset,
  };
}
