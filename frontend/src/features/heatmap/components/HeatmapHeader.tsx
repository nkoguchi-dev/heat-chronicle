import { ThemeToggle } from '@/features/shared/components/ThemeToggle';

import { LoadingStatus } from './LoadingStatus';

import type { ProgressEvent } from '../types/api';

interface HeatmapHeaderProps {
  progress: ProgressEvent | null;
}

export function HeatmapHeader({ progress }: HeatmapHeaderProps): React.JSX.Element {
  return (
    <div className="relative flex w-full items-center justify-center">
      <h1 className="text-xl font-bold md:text-2xl">Heat Chronicle</h1>
      <div className="absolute right-0 flex items-center gap-2">
        {progress && (
          <LoadingStatus
            state="progress"
            message={`${progress.year}年${progress.month}月を取得中...`}
            progress={progress}
            variant="compact"
          />
        )}
        <ThemeToggle />
      </div>
    </div>
  );
}
