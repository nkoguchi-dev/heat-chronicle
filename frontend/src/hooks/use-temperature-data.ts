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
  fetching: boolean;
  progress: ProgressEvent | null;
  error: string | null;
  fetchData: (stationId: number, startYear: number, endYear: number) => void;
}

export function useTemperatureData(): UseTemperatureDataReturn {
  const [records, setRecords] = useState<TemperatureRecord[]>([]);
  const [loading, setLoading] = useState(false);
  const [fetching, setFetching] = useState(false);
  const [progress, setProgress] = useState<ProgressEvent | null>(null);
  const [error, setError] = useState<string | null>(null);
  const fetchIdRef = useRef(0);
  const abortControllerRef = useRef<AbortController | null>(null);

  const fetchData = useCallback(
    (stationId: number, startYear: number, endYear: number) => {
      // Cancel any existing fetch sequence
      abortControllerRef.current?.abort();
      const controller = new AbortController();
      abortControllerRef.current = controller;
      const myFetchId = ++fetchIdRef.current;

      setLoading(true);
      setFetching(false);
      setProgress(null);
      setError(null);
      setRecords([]);

      apiClient
        .get<TemperatureResponse>(
          `/api/temperature/${stationId}?start_year=${startYear}&end_year=${endYear}`,
          { signal: controller.signal }
        )
        .then(async (response) => {
          if (fetchIdRef.current !== myFetchId) return;

          setRecords(response.data);
          setLoading(false);

          if (!response.metadata.fetching_required) return;

          // 未取得月のリストを作成
          const fetchedSet = new Set(response.metadata.fetched_months);
          const monthsToFetch: { year: number; month: number }[] = [];
          const now = new Date();
          const currentYear = now.getFullYear();
          const currentMonth = now.getMonth() + 1;

          for (let y = endYear; y >= startYear; y--) {
            for (let m = 12; m >= 1; m--) {
              if (y > currentYear || (y === currentYear && m > currentMonth))
                continue;
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
            if (fetchIdRef.current !== myFetchId) break;

            const { year, month } = monthsToFetch[i];
            setProgress({ year, month, completed: i, total });

            try {
              const monthData =
                await apiClient.get<MonthTemperatureResponse>(
                  `/api/temperature/${stationId}/fetch-month?year=${year}&month=${month}`,
                  { signal: controller.signal }
                );

              if (fetchIdRef.current !== myFetchId) break;

              // 取得した月のデータをマージ
              if (monthData.records.length > 0) {
                setRecords((prev) => [...prev, ...monthData.records]);
              }
            } catch (err) {
              if (err instanceof DOMException && err.name === "AbortError") {
                break;
              }
              console.error(
                `Failed to fetch ${year}-${month}:`,
                err
              );
              // 個別の月の失敗は無視して続行
            }
          }

          if (fetchIdRef.current === myFetchId) {
            setFetching(false);
            setProgress(null);
          }
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

  return { records, loading, fetching, progress, error, fetchData };
}
