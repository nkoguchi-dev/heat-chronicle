import { LoadingStatus } from './LoadingStatus';

import type { ProgressEvent } from '../types/api';
import type { TemperatureLoadError, TemperatureLoadOperation } from '../types/temperature-data';

interface PrimaryLoadingStatusProps {
  stationError: string | null;
  stationLoadingPhase: 'prefectures' | 'stations' | null;
  temperatureError: TemperatureLoadError | null;
  activeOperation: TemperatureLoadOperation | null;
  progress: ProgressEvent | null;
  onRetryStation: () => void;
  onRetryTemperature: () => void;
}

export function PrimaryLoadingStatus(props: PrimaryLoadingStatusProps): React.JSX.Element | null {
  if (props.stationError) {
    return <LoadingStatus state="error" message={props.stationError} onRetry={props.onRetryStation} />;
  }
  if (props.stationLoadingPhase) {
    const message =
      props.stationLoadingPhase === 'prefectures'
        ? '都道府県一覧を読み込んでいます...'
        : '観測地点一覧を読み込んでいます...';
    return <LoadingStatus state="loading" message={message} />;
  }
  if (props.temperatureError?.operation.mode === 'initial') {
    return <LoadingStatus state="error" message={props.temperatureError.message} onRetry={props.onRetryTemperature} />;
  }
  if (props.activeOperation?.mode !== 'initial' || props.progress?.total === 1) return null;
  return (
    <LoadingStatus
      state={props.progress ? 'progress' : 'loading'}
      message={
        props.progress
          ? `${props.progress.year}年${props.progress.month}月を取得中...`
          : '気温データを読み込んでいます...'
      }
      progress={props.progress ?? undefined}
    />
  );
}
