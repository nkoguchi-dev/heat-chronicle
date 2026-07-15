'use client';

import { useCallback, useEffect, useRef, useState } from 'react';

import { apiClient } from '@/features/shared/libs/api-client';
import type {
  MonthTemperatureResponse,
  ProgressEvent,
  TemperatureRecord,
  TemperatureResponse,
} from '@/features/heatmap/types/api';

export type TemperatureLoadMode = 'initial' | 'more';

export interface TemperatureLoadOperation {
  mode: TemperatureLoadMode;
  stationId: number;
  endYear: number;
}

export interface TemperatureLoadError {
  operation: TemperatureLoadOperation;
  message: string;
}

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

function buildMonthsToFetch(
  startYear: number,
  endYear: number,
  fetchedMonths: string[],
): { year: number; month: number }[] {
  const fetchedSet = new Set(fetchedMonths);
  const months: { year: number; month: number }[] = [];
  const now = new Date();
  const currentYear = now.getFullYear();
  const currentMonth = now.getMonth() + 1;

  for (let y = endYear; y >= startYear; y--) {
    for (let m = 12; m >= 1; m--) {
      if (y > currentYear || (y === currentYear && m > currentMonth)) continue;
      const key = `${y}-${String(m).padStart(2, '0')}`;
      if (!fetchedSet.has(key)) {
        months.push({ year: y, month: m });
      }
    }
  }

  return months;
}

function mergeRecords(current: TemperatureRecord[], incoming: TemperatureRecord[]): TemperatureRecord[] {
  if (incoming.length === 0) return current;

  const next = [...current];
  const indexByDate = new Map(current.map((record, index) => [record.date, index]));

  for (const record of incoming) {
    const existingIndex = indexByDate.get(record.date);
    if (existingIndex === undefined) {
      indexByDate.set(record.date, next.length);
      next.push(record);
    } else {
      next[existingIndex] = record;
    }
  }

  return next;
}

function isAbortError(error: unknown): boolean {
  return error instanceof DOMException && error.name === 'AbortError';
}

async function waitForNextRequest(signal: AbortSignal): Promise<void> {
  await new Promise<void>((resolve, reject) => {
    const timer = setTimeout(resolve, 1000);
    signal.addEventListener(
      'abort',
      () => {
        clearTimeout(timer);
        reject(new DOMException('Aborted', 'AbortError'));
      },
      { once: true },
    );
  });
}

async function fetchMissingMonths(
  stationId: number,
  months: { year: number; month: number }[],
  controller: AbortController,
  fetchId: number,
  fetchIdRef: React.RefObject<number>,
  setRecords: React.Dispatch<React.SetStateAction<TemperatureRecord[]>>,
  setProgress: React.Dispatch<React.SetStateAction<ProgressEvent | null>>,
): Promise<number> {
  const total = months.length;
  let failedCount = 0;

  for (let i = 0; i < months.length; i++) {
    if (fetchIdRef.current !== fetchId || controller.signal.aborted) break;

    const { year, month } = months[i];
    setProgress({ year, month, completed: i, total });

    try {
      const monthData = await apiClient.get<MonthTemperatureResponse>(
        `/api/temperature/${stationId}/fetch-month?year=${year}&month=${month}`,
        { signal: controller.signal },
      );

      if (fetchIdRef.current !== fetchId) break;

      setRecords((current) => mergeRecords(current, monthData.records));
      setProgress({ year, month, completed: i + 1, total });
    } catch (requestError) {
      if (isAbortError(requestError)) break;
      failedCount += 1;
      console.error(`Failed to fetch ${year}-${month}:`, requestError);
    }

    if (i < months.length - 1 && !controller.signal.aborted) {
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

function getErrorMessage(operation: TemperatureLoadOperation, partialFailure: boolean): string {
  if (partialFailure) {
    return '一部の月の気温データを取得できませんでした。';
  }
  if (operation.mode === 'more') {
    return `〜${operation.endYear}年の気温データを取得できませんでした。`;
  }
  return '気温データを取得できませんでした。';
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

  const finishOperation = useCallback((operation: TemperatureLoadOperation, fetchId: number) => {
    if (fetchIdRef.current !== fetchId) return;
    if (activeOperationRef.current === operation) {
      activeOperationRef.current = null;
    }
    abortControllerRef.current = null;
    setActiveOperation(null);
    setProgress(null);
  }, []);

  const executeOperation = useCallback(
    (operation: TemperatureLoadOperation) => {
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
            setRecords((current) => mergeRecords(current, response.data));
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
              message: getErrorMessage(operation, true),
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
              message: getErrorMessage(operation, false),
            });
            finishOperation(operation, fetchId);
          }
        });
    },
    [finishOperation],
  );

  const fetchData = useCallback(
    (stationId: number, endYear: number) => {
      executeOperation({ mode: 'initial', stationId, endYear });
    },
    [executeOperation],
  );

  const fetchMoreData = useCallback(
    (stationId: number, endYear: number) => {
      if (activeOperationRef.current !== null || failedOperationRef.current !== null) {
        return;
      }
      executeOperation({ mode: 'more', stationId, endYear });
    },
    [executeOperation],
  );

  const retry = useCallback(() => {
    const operation = failedOperationRef.current;
    if (operation) {
      executeOperation(operation);
    }
  }, [executeOperation]);

  const reset = useCallback(() => {
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
