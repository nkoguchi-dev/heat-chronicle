import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, expect, it, vi } from 'vitest';

import { LoadMoreButton } from '@/features/heatmap/components/LoadMoreButton';

describe('LoadMoreButton', () => {
  it('shows the next year and invokes the callback', async () => {
    const onLoadMore = vi.fn();
    const user = userEvent.setup();
    render(<LoadMoreButton nextEndYear={2015} onLoadMore={onLoadMore} />);

    await user.click(screen.getByRole('button', { name: '〜2015年のデータを読み込む' }));
    expect(onLoadMore).toHaveBeenCalledOnce();
  });
});
