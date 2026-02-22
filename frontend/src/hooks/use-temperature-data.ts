"use client";

import { useCallback, useRef, useState } from "react";

import { apiClient } from "@/features/shared/libs/api-client";
import { pollJobStatus, startFetchJob } from "@/features/shared/libs/polling-client";
import type {
  ProgressEvent,
  TemperatureRecord,
  TemperatureResponse,
} from "@/types/api";

interface UseTemperatureDataReturn {
  records: TemperatureRecord[];
  loading: boolean;
  streaming: boolean;
  progress: ProgressEvent | null;
  error: string | null;
  fetchData: (stationId: number, startYear: number, endYear: number) => void;
}

export function useTemperatureData(): UseTemperatureDataReturn {
  const [records, setRecords] = useState<TemperatureRecord[]>([]);
  const [loading, setLoading] = useState(false);
  const [streaming, setStreaming] = useState(false);
  const [progress, setProgress] = useState<ProgressEvent | null>(null);
  const [error, setError] = useState<string | null>(null);
  const cancelRef = useRef<(() => void) | null>(null);

  const fetchData = useCallback(
    (stationId: number, startYear: number, endYear: number) => {
      // Cancel any existing polling
      if (cancelRef.current) {
        cancelRef.current();
        cancelRef.current = null;
      }

      setLoading(true);
      setStreaming(false);
      setProgress(null);
      setError(null);
      setRecords([]);

      // First, fetch cached data via REST
      apiClient
        .get<TemperatureResponse>(
          `/api/temperature/${stationId}?start_year=${startYear}&end_year=${endYear}`
        )
        .then(async (response) => {
          setRecords(response.data);
          setLoading(false);

          if (response.metadata.fetching_required) {
            setStreaming(true);

            try {
              const job = await startFetchJob(stationId, startYear, endYear);
              const { promise, cancel } = pollJobStatus(
                stationId,
                job.job_id,
                (status) => {
                  if (status.year && status.month) {
                    setProgress({
                      year: status.year,
                      month: status.month,
                      completed: status.completed,
                      total: status.total,
                    });
                  }
                }
              );
              cancelRef.current = cancel;

              await promise;
              // ジョブ完了後にデータを再取得
              const finalData = await apiClient.get<TemperatureResponse>(
                `/api/temperature/${stationId}?start_year=${startYear}&end_year=${endYear}`
              );
              setRecords(finalData.data);
              setStreaming(false);
              setProgress(null);
              cancelRef.current = null;
            } catch (err) {
              setError(
                err instanceof Error ? err.message : "Fetch job failed"
              );
              setStreaming(false);
              cancelRef.current = null;
            }
          }
        })
        .catch((err) => {
          setError(err.message);
          setLoading(false);
        });
    },
    []
  );

  return { records, loading, streaming, progress, error, fetchData };
}
