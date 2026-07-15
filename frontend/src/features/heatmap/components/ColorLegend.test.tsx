import { render, screen } from '@testing-library/react';
import { describe, expect, it, vi } from 'vitest';

import { ColorLegend } from '@/features/heatmap/components/ColorLegend';

describe('ColorLegend', () => {
  it('renders the full label range and draws the gradient', () => {
    const context = {
      fillStyle: '',
      scale: vi.fn(),
      fillRect: vi.fn(),
    } as unknown as CanvasRenderingContext2D;
    vi.spyOn(HTMLCanvasElement.prototype, 'getContext').mockReturnValue(context);
    vi.spyOn(HTMLElement.prototype, 'clientWidth', 'get').mockReturnValue(300);

    render(<ColorLegend />);

    expect(screen.getByText('-10℃')).toBeInTheDocument();
    expect(screen.getByText('40℃')).toBeInTheDocument();
    expect(context.fillRect).toHaveBeenCalledTimes(300);
  });
});
