import { fireEvent, render } from '@testing-library/react';
import { describe, expect, it, vi } from 'vitest';

import { Heatmap } from '@/features/heatmap/components/Heatmap';
import { LEFT_MARGIN, TOP_MARGIN } from '@/features/heatmap/libs/heatmap-canvas';

describe('Heatmap', () => {
  it('draws records and shows and clears the hovered-cell tooltip', () => {
    const context = {
      fillStyle: '',
      font: '',
      textAlign: 'start',
      scale: vi.fn(),
      clearRect: vi.fn(),
      fillText: vi.fn(),
      fillRect: vi.fn(),
    } as unknown as CanvasRenderingContext2D;
    vi.spyOn(HTMLCanvasElement.prototype, 'getContext').mockReturnValue(context);
    vi.spyOn(HTMLCanvasElement.prototype, 'getBoundingClientRect').mockReturnValue({
      x: 0,
      y: 0,
      top: 0,
      left: 0,
      right: 1148,
      bottom: 42,
      width: 1148,
      height: 42,
      toJSON: () => ({}),
    });

    const { container, queryByText } = render(
      <Heatmap
        records={[{ date: '2025-01-01', max_temp: 10, min_temp: 0, avg_temp: 5 }]}
        startYear={2025}
        endYear={2025}
        tempType="max"
      />,
    );
    const canvas = container.querySelector('canvas');
    expect(canvas).not.toBeNull();
    expect(context.fillRect).toHaveBeenCalledTimes(366);

    fireEvent.mouseMove(canvas!, { clientX: LEFT_MARGIN, clientY: TOP_MARGIN });
    expect(queryByText('2025年1月1日: 10.0℃')).toBeInTheDocument();

    fireEvent.mouseLeave(canvas!);
    expect(queryByText('2025年1月1日: 10.0℃')).not.toBeInTheDocument();
  });
});
