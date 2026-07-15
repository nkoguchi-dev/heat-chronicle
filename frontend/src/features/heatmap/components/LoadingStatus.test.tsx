import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, expect, it, vi } from 'vitest';

import { LoadingStatus } from '@/features/heatmap/components/LoadingStatus';

describe('LoadingStatus', () => {
  it('announces a loading message', () => {
    render(<LoadingStatus state="loading" message="読み込み中" />);

    expect(screen.getByRole('status')).toHaveTextContent('読み込み中');
  });

  it('shows progress and safely handles a zero total', () => {
    render(
      <LoadingStatus state="progress" message="取得中" progress={{ year: 2026, month: 1, completed: 1, total: 0 }} />,
    );

    expect(screen.getByText('1/0 (100%)')).toBeInTheDocument();
    expect(screen.getByRole('progressbar', { name: '取得中 100%' })).toBeInTheDocument();
  });

  it('renders a compact accessible status', () => {
    render(<LoadingStatus state="loading" message="1月を取得中" variant="compact" />);

    expect(screen.getByRole('status', { name: '1月を取得中' })).toBeInTheDocument();
  });

  it('exposes an error and retries on request', async () => {
    const retry = vi.fn();
    const user = userEvent.setup();
    render(<LoadingStatus state="error" message="取得失敗" onRetry={retry} />);

    expect(screen.getByRole('alert')).toHaveTextContent('取得失敗');
    await user.click(screen.getByRole('button', { name: '再試行' }));
    expect(retry).toHaveBeenCalledOnce();
  });
});
