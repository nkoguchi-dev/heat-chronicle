"use client";

import { useCallback, useRef, useState } from "react";

import { apiClient } from "@/features/shared/libs/api-client";
import { connectSSE } from "@/features/shared/libs/sse-client";
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
  const eventSourceRef = useRef<EventSource | null>(null);

  const fetchData = useCallback(
    (stationId: number, startYear: number, endYear: number) => {
      // Close any existing SSE connection
      if (eventSourceRef.current) {
        eventSourceRef.current.close();
        eventSourceRef.current = null;
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
        .then((response) => {
          setRecords(response.data);
          setLoading(false);

          if (response.metadata.fetching_required) {
            // Start SSE streaming for missing data
            setStreaming(true);
            const es = connectSSE(
              `/api/temperature/${stationId}/stream?start_year=${startYear}&end_year=${endYear}`,
              {
                onProgress: (data) => {
                  setProgress(data);
                },
                onData: (data) => {
                  setRecords((prev) => [...prev, ...data.records]);
                },
                onComplete: () => {
                  setStreaming(false);
                  setProgress(null);
                  eventSourceRef.current = null;
                },
                onError: (data) => {
                  setError(data.message);
                  if (!data.year) {
                    // Fatal error, stop streaming
                    setStreaming(false);
                    eventSourceRef.current = null;
                  }
                },
              }
            );
            eventSourceRef.current = es;
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
