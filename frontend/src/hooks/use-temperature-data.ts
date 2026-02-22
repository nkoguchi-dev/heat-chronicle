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
  const cancelRef = useRef(false);

  const fetchData = useCallback(
    (stationId: number, startYear: number, endYear: number) => {
      // Cancel any existing fetch sequence
      cancelRef.current = true;

      setLoading(true);
      setFetching(false);
      setProgress(null);
      setError(null);
      setRecords([]);

      // Allow cancellation for this new sequence
      cancelRef.current = false;

      apiClient
        .get<TemperatureResponse>(
          `/api/temperature/${stationId}?start_year=${startYear}&end_year=${endYear}`
        )
        .then(async (response) => {
          if (cancelRef.current) return;

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
            if (cancelRef.current) break;

            const { year, month } = monthsToFetch[i];
            setProgress({ year, month, completed: i, total });

            try {
              const monthData =
                await apiClient.get<MonthTemperatureResponse>(
                  `/api/temperature/${stationId}/fetch-month?year=${year}&month=${month}`
                );

              if (cancelRef.current) break;

              // 取得した月のデータをマージ
              if (monthData.records.length > 0) {
                setRecords((prev) => [...prev, ...monthData.records]);
              }
            } catch (err) {
              console.error(
                `Failed to fetch ${year}-${month}:`,
                err
              );
              // 個別の月の失敗は無視して続行
            }
          }

          if (!cancelRef.current) {
            setFetching(false);
            setProgress(null);
          }
        })
        .catch((err) => {
          if (!cancelRef.current) {
            setError(err.message);
            setLoading(false);
          }
        });
    },
    []
  );

  return { records, loading, fetching, progress, error, fetchData };
}
