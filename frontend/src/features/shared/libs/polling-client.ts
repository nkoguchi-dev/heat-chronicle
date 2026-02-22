import { apiClient } from "@/features/shared/libs/api-client";
import type { FetchJobResponse, JobStatusResponse } from "@/types/api";

export async function startFetchJob(
  stationId: number,
  startYear: number,
  endYear: number
): Promise<FetchJobResponse> {
  return apiClient.post<FetchJobResponse>(
    `/api/temperature/${stationId}/fetch?start_year=${startYear}&end_year=${endYear}`
  );
}

export function pollJobStatus(
  stationId: number,
  jobId: string,
  onProgress: (status: JobStatusResponse) => void,
  intervalMs: number = 2000
): { promise: Promise<void>; cancel: () => void } {
  let cancelled = false;
  let retryCount = 0;
  const MAX_RETRIES = 3;

  const promise = new Promise<void>((resolve, reject) => {
    const poll = async () => {
      if (cancelled) return;

      try {
        const status = await apiClient.get<JobStatusResponse>(
          `/api/temperature/${stationId}/fetch/status?job_id=${jobId}`
        );
        retryCount = 0;

        onProgress(status);

        if (status.status === "complete") {
          resolve();
        } else if (status.status === "error") {
          reject(new Error(status.message || "Fetch job failed"));
        } else if (!cancelled) {
          setTimeout(poll, intervalMs);
        }
      } catch {
        retryCount++;
        if (retryCount >= MAX_RETRIES) {
          reject(new Error("ポーリングが複数回失敗しました"));
        } else if (!cancelled) {
          setTimeout(poll, intervalMs * 2);
        }
      }
    };
    poll();
  });

  const cancel = () => {
    cancelled = true;
  };

  return { promise, cancel };
}
