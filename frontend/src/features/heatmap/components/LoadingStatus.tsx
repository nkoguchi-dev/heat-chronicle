"use client";

import { AlertCircle, Loader2 } from "lucide-react";

import { Button } from "@/components/ui/button";
import { Progress } from "@/components/ui/progress";
import type { ProgressEvent } from "@/types/api";

interface LoadingStatusProps {
  state: "loading" | "progress" | "error";
  message: string;
  progress?: ProgressEvent;
  onRetry?: () => void;
}

export function LoadingStatus({
  state,
  message,
  progress,
  onRetry,
}: LoadingStatusProps) {
  const percent = progress
    ? Math.round((progress.completed / Math.max(progress.total, 1)) * 100)
    : 0;

  if (state === "error") {
    return (
      <div
        className="flex w-full max-w-xl flex-col items-center gap-3 rounded-md border border-destructive/40 bg-destructive/10 px-4 py-3 text-center text-sm text-destructive sm:flex-row sm:justify-between sm:text-left"
        role="alert"
      >
        <span className="inline-flex items-center gap-2">
          <AlertCircle aria-hidden="true" className="size-4 shrink-0" />
          {message}
        </span>
        {onRetry && (
          <Button variant="outline" size="sm" onClick={onRetry}>
            再試行
          </Button>
        )}
      </div>
    );
  }

  return (
    <div
      className="w-full max-w-xl space-y-2 rounded-md border bg-muted/30 px-4 py-3"
      role="status"
      aria-live="polite"
      aria-atomic="true"
    >
      <div className="flex items-center justify-between gap-3 text-sm text-muted-foreground">
        <span className="inline-flex min-w-0 items-center gap-2">
          <Loader2
            aria-hidden="true"
            className="size-4 shrink-0 animate-spin motion-reduce:animate-none"
          />
          <span>{message}</span>
        </span>
        {state === "progress" && progress && (
          <span className="shrink-0 tabular-nums">
            {progress.completed}/{progress.total} ({percent}%)
          </span>
        )}
      </div>
      {state === "progress" && progress && (
        <Progress
          value={percent}
          aria-label={`${message} ${percent}%`}
        />
      )}
    </div>
  );
}
