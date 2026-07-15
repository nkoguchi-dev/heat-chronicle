import { render, screen } from '@testing-library/react';
import { describe, expect, it, vi } from 'vitest';

import { StationSelector } from '@/features/heatmap/components/StationSelector';
import type { Prefecture, Station } from '@/features/heatmap/types/api';

const PREFECTURES: Prefecture[] = [{ prec_no: 44, name: '大分県' }];
const STATIONS: Station[] = [
  {
    id: 4,
    station_name: '大分',
    prec_no: 44,
    block_no: '47815',
    station_type: 's',
    latitude: null,
    longitude: null,
    earliest_year: 1887,
  },
];

describe('StationSelector', () => {
  it('renders selected prefecture and station controls', () => {
    render(
      <StationSelector
        prefectures={PREFECTURES}
        stations={STATIONS}
        selectedPrecNo={44}
        selectedStationId={4}
        isLoadingPrefectures={false}
        isLoadingStations={false}
        onPrefectureChange={vi.fn()}
        onSelect={vi.fn()}
      />,
    );

    const controls = screen.getAllByRole('combobox');
    expect(controls).toHaveLength(2);
    expect(controls[0]).not.toBeDisabled();
    expect(controls[1]).not.toBeDisabled();
  });

  it('disables both controls while prefectures are loading', () => {
    render(
      <StationSelector
        prefectures={[]}
        stations={[]}
        selectedPrecNo={null}
        selectedStationId={null}
        isLoadingPrefectures
        isLoadingStations={false}
        onPrefectureChange={vi.fn()}
        onSelect={vi.fn()}
      />,
    );

    for (const control of screen.getAllByRole('combobox')) expect(control).toBeDisabled();
  });
});
