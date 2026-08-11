import { LoadingStatus } from './LoadingStatus';

import type { ProgressEvent } from '../types/api';
import type { TemperatureLoadError, TemperatureLoadOperation } from '../types/temperature-data';

interface LoadMoreStatusProps {
  error: TemperatureLoadError | null;
  activeOperation: TemperatureLoadOperation | null;
  progress: ProgressEvent | null;
  onRetry: () => void;
}

export function LoadMoreStatus({
  error,
  activeOperation,
  progress,
  onRetry,
}: LoadMoreStatusProps): React.JSX.Element | null {
  if (error?.operation.mode === 'more') {
    return <LoadingStatus state="error" message={error.message} onRetry={onRetry} />;
  }
  if (activeOperation?.mode !== 'more') return null;
  return (
    <LoadingStatus
      state={progress ? 'progress' : 'loading'}
      message={
        progress
          ? `${progress.year}年${progress.month}月を取得中...`
          : `〜${activeOperation.endYear}年のデータを読み込んでいます...`
      }
      progress={progress ?? undefined}
    />
  );
}
