import type {
  CompleteEvent,
  DataEvent,
  ErrorEvent,
  ProgressEvent,
} from "@/types/api";

const API_BASE_URL =
  process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export interface SSEHandlers {
  onProgress?: (data: ProgressEvent) => void;
  onData?: (data: DataEvent) => void;
  onComplete?: (data: CompleteEvent) => void;
  onError?: (data: ErrorEvent) => void;
}

export function connectSSE(path: string, handlers: SSEHandlers): EventSource {
  const url = `${API_BASE_URL}${path}`;
  const eventSource = new EventSource(url);

  eventSource.addEventListener("progress", (e) => {
    const data = JSON.parse(e.data) as ProgressEvent;
    handlers.onProgress?.(data);
  });

  eventSource.addEventListener("data", (e) => {
    const data = JSON.parse(e.data) as DataEvent;
    handlers.onData?.(data);
  });

  eventSource.addEventListener("complete", (e) => {
    const data = JSON.parse(e.data) as CompleteEvent;
    handlers.onComplete?.(data);
    eventSource.close();
  });

  eventSource.addEventListener("error", (e) => {
    if (e instanceof MessageEvent && e.data) {
      const data = JSON.parse(e.data) as ErrorEvent;
      handlers.onError?.(data);
    } else {
      handlers.onError?.({ message: "SSE connection error" });
      eventSource.close();
    }
  });

  return eventSource;
}
