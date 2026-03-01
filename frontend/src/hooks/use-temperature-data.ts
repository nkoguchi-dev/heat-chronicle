"use client";

import { useCallback, useRef, useState } from "react";

import { apiClient } from "@/features/shared/libs/api-client";
import type {
  MonthTemperatureResponse,
  ProgressEvent,
  TemperatureRecord,
  TemperatureResponse,
} from "@/types/api";

interface UseTemperatureDataReturn {
  records: TemperatureRecord[];
  loading: boolean;
  loadingMore: boolean;
  fetching: boolean;
  progress: ProgressEvent | null;
  error: string | null;
  hasOlderData: boolean;
  nextEndYear: number | null;
  startYear: number | null;
  fetchData: (stationId: number, endYear: number) => void;
  fetchMoreData: (stationId: number, endYear: number) => void;
}

async function runScrapingFlow(
  stationId: number,
  startYear: number,
  endYear: number,
  fetchedMonths: string[],
  controller: AbortController,
  fetchId: number,
  fetchIdRef: React.RefObject<number>,
  setRecords: React.Dispatch<React.SetStateAction<TemperatureRecord[]>>,
  setFetching: React.Dispatch<React.SetStateAction<boolean>>,
  setProgress: React.Dispatch<React.SetStateAction<ProgressEvent | null>>
): Promise<void> {
  const fetchedSet = new Set(fetchedMonths);
  const monthsToFetch: { year: number; month: number }[] = [];
  const now = new Date();
  const currentYear = now.getFullYear();
  const currentMonth = now.getMonth() + 1;

  for (let y = endYear; y >= startYear; y--) {
    for (let m = 12; m >= 1; m--) {
      if (y > currentYear || (y === currentYear && m > currentMonth)) continue;
      const key = `${y}-${String(m).padStart(2, "0")}`;
      if (!fetchedSet.has(key)) {
        monthsToFetch.push({ year: y, month: m });
      }
    }
  }

  if (monthsToFetch.length === 0) return;

  setFetching(true);
  const total = monthsToFetch.length;

  for (let i = 0; i < monthsToFetch.length; i++) {
    if (fetchIdRef.current !== fetchId) break;

    const { year, month } = monthsToFetch[i];
    setProgress({ year, month, completed: i, total });

    try {
      const monthData = await apiClient.get<MonthTemperatureResponse>(
        `/api/temperature/${stationId}/fetch-month?year=${year}&month=${month}`,
        { signal: controller.signal }
      );

      if (fetchIdRef.current !== fetchId) break;

      if (monthData.records.length > 0) {
        setRecords((prev) => [...prev, ...monthData.records]);
      }

      // Rate limit: wait 1s between requests
      if (i < monthsToFetch.length - 1) {
        await new Promise<void>((resolve, reject) => {
          const timer = setTimeout(resolve, 1000);
          controller.signal.addEventListener(
            "abort",
            () => {
              clearTimeout(timer);
              reject(new DOMException("Aborted", "AbortError"));
            },
            { once: true }
          );
        });
      }
    } catch (err) {
      if (err instanceof DOMException && err.name === "AbortError") {
        break;
      }
      console.error(`Failed to fetch ${year}-${month}:`, err);
    }
  }

  if (fetchIdRef.current === fetchId) {
    setFetching(false);
    setProgress(null);
  }
}

export function useTemperatureData(): UseTemperatureDataReturn {
  const [records, setRecords] = useState<TemperatureRecord[]>([]);
  const [loading, setLoading] = useState(false);
  const [loadingMore, setLoadingMore] = useState(false);
  const [fetching, setFetching] = useState(false);
  const [progress, setProgress] = useState<ProgressEvent | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [hasOlderData, setHasOlderData] = useState(false);
  const [nextEndYear, setNextEndYear] = useState<number | null>(null);
  const [startYear, setStartYear] = useState<number | null>(null);
  const fetchIdRef = useRef(0);
  const abortControllerRef = useRef<AbortController | null>(null);
  const loadingMoreRef = useRef(false);

  const fetchData = useCallback(
    (stationId: number, endYear: number) => {
      // Cancel any existing fetch/fetchMore sequence
      abortControllerRef.current?.abort();
      loadingMoreRef.current = false;
      const controller = new AbortController();
      abortControllerRef.current = controller;
      const myFetchId = ++fetchIdRef.current;

      setLoading(true);
      setLoadingMore(false);
      setFetching(false);
      setProgress(null);
      setError(null);
      setRecords([]);
      setHasOlderData(false);
      setNextEndYear(null);
      setStartYear(null);

      apiClient
        .get<TemperatureResponse>(
          `/api/temperature/${stationId}?end_year=${endYear}`,
          { signal: controller.signal }
        )
        .then(async (response) => {
          if (fetchIdRef.current !== myFetchId) return;

          setRecords(response.data);
          setStartYear(response.metadata.start_year);
          setHasOlderData(response.metadata.has_older_data);
          setNextEndYear(response.metadata.next_end_year);
          setLoading(false);

          if (!response.metadata.fetching_required) return;

          await runScrapingFlow(
            stationId,
            response.metadata.start_year,
            endYear,
            response.metadata.fetched_months,
            controller,
            myFetchId,
            fetchIdRef,
            setRecords,
            setFetching,
            setProgress
          );
        })
        .catch((err) => {
          if (err instanceof DOMException && err.name === "AbortError") return;
          if (fetchIdRef.current === myFetchId) {
            setError(err.message);
            setLoading(false);
          }
        });
    },
    []
  );

  const fetchMoreData = useCallback(
    (stationId: number, endYear: number) => {
      // Block double execution
      if (loadingMoreRef.current) return;
      loadingMoreRef.current = true;

      const controller = abortControllerRef.current ?? new AbortController();
      abortControllerRef.current = controller;
      const myFetchId = fetchIdRef.current;

      setLoadingMore(true);
      setError(null);

      apiClient
        .get<TemperatureResponse>(
          `/api/temperature/${stationId}?end_year=${endYear}`,
          { signal: controller.signal }
        )
        .then(async (response) => {
          if (fetchIdRef.current !== myFetchId) return;

          setRecords((prev) => [...prev, ...response.data]);
          setStartYear(response.metadata.start_year);
          setHasOlderData(response.metadata.has_older_data);
          setNextEndYear(response.metadata.next_end_year);
          setLoadingMore(false);
          loadingMoreRef.current = false;

          if (!response.metadata.fetching_required) return;

          await runScrapingFlow(
            stationId,
            response.metadata.start_year,
            endYear,
            response.metadata.fetched_months,
            controller,
            myFetchId,
            fetchIdRef,
            setRecords,
            setFetching,
            setProgress
          );
        })
        .catch((err) => {
          if (err instanceof DOMException && err.name === "AbortError") return;
          if (fetchIdRef.current === myFetchId) {
            setError(err.message);
            setLoadingMore(false);
            loadingMoreRef.current = false;
          }
        });
    },
    []
  );

  return {
    records,
    loading,
    loadingMore,
    fetching,
    progress,
    error,
    hasOlderData,
    nextEndYear,
    startYear,
    fetchData,
    fetchMoreData,
  };
}
