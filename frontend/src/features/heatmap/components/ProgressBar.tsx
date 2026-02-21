"use client";

import { Progress } from "@/components/ui/progress";
import type { ProgressEvent } from "@/types/api";

interface ProgressBarProps {
  progress: ProgressEvent | null;
  streaming: boolean;
}

export function ProgressBar({ progress, streaming }: ProgressBarProps) {
  if (!streaming || !progress) return null;

  const percent =
    progress.total > 0
      ? Math.round((progress.completed / progress.total) * 100)
      : 0;

  return (
    <div className="w-full max-w-xl space-y-1">
      <div className="flex justify-between text-sm text-muted-foreground">
        <span>
          {progress.year}年{progress.month}月を取得中...
        </span>
        <span>
          {progress.completed}/{progress.total} ({percent}%)
        </span>
      </div>
      <Progress value={percent} />
    </div>
  );
}
