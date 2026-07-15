import { render, screen } from '@testing-library/react';
import { beforeEach, describe, expect, it, vi } from 'vitest';

import { HeatmapPage } from '@/features/heatmap/page';
import { useStationOptions } from '@/features/heatmap/hooks/use-station-options';
import { useTemperatureData } from '@/features/heatmap/hooks/use-temperature-data';
import { useUrlParams } from '@/features/heatmap/hooks/use-url-params';

vi.mock('@/features/heatmap/hooks/use-station-options');
vi.mock('@/features/heatmap/hooks/use-temperature-data');
vi.mock('@/features/heatmap/hooks/use-url-params');
vi.mock('@/features/shared/components/ThemeToggle', () => ({
  ThemeToggle: () => <button type="button">theme</button>,
}));

const useStationOptionsMock = vi.mocked(useStationOptions);
const useTemperatureDataMock = vi.mocked(useTemperatureData);
const useUrlParamsMock = vi.mocked(useUrlParams);

beforeEach(() => {
  useUrlParamsMock.mockReturnValue({
    initialParams: { station: 4, pref: 44, type: 'max' },
    updateUrl: vi.fn(),
  });
  useStationOptionsMock.mockReturnValue({
    prefectures: [{ prec_no: 44, name: '大分県' }],
    stations: [],
    loadingPhase: 'stations',
    error: null,
    retry: vi.fn(),
  });
  useTemperatureDataMock.mockReturnValue({
    records: [],
    activeOperation: null,
    progress: null,
    error: null,
    hasOlderData: false,
    nextEndYear: null,
    startYear: null,
    fetchData: vi.fn(),
    fetchMoreData: vi.fn(),
    retry: vi.fn(),
    reset: vi.fn(),
  });
});

describe('HeatmapPage', () => {
  it('renders the page shell and current loading phase', () => {
    render(<HeatmapPage />);

    expect(screen.getByRole('heading', { name: 'Heat Chronicle' })).toBeInTheDocument();
    expect(screen.getByRole('status')).toHaveTextContent('観測地点一覧を読み込んでいます');
    expect(screen.getByRole('link', { name: /ソースコードをGitHubで開く/ })).toBeInTheDocument();
  });

  it('prioritizes a retryable station option error', () => {
    useStationOptionsMock.mockReturnValue({
      prefectures: [],
      stations: [],
      loadingPhase: null,
      error: { phase: 'prefectures', message: '都道府県一覧を取得できませんでした。' },
      retry: vi.fn(),
    });

    render(<HeatmapPage />);

    expect(screen.getByRole('alert')).toHaveTextContent('都道府県一覧を取得できませんでした');
  });

  it('renders data, historical loading, legend, and the scrollable heatmap region', () => {
    useStationOptionsMock.mockReturnValue({
      prefectures: [{ prec_no: 44, name: '大分県' }],
      stations: [],
      loadingPhase: null,
      error: null,
      retry: vi.fn(),
    });
    useTemperatureDataMock.mockReturnValue({
      records: [],
      activeOperation: { mode: 'more', stationId: 4, endYear: 2016 },
      progress: null,
      error: null,
      hasOlderData: true,
      nextEndYear: 2006,
      startYear: 2016,
      fetchData: vi.fn(),
      fetchMoreData: vi.fn(),
      retry: vi.fn(),
      reset: vi.fn(),
    });
    vi.spyOn(HTMLCanvasElement.prototype, 'getContext').mockReturnValue(null);

    render(<HeatmapPage />);

    expect(screen.getByRole('region', { name: '気温ヒートマップ' })).toBeInTheDocument();
    expect(screen.getByRole('status')).toHaveTextContent('〜2016年のデータを読み込んでいます');
    expect(screen.getByText('-10℃')).toBeInTheDocument();
  });
});
