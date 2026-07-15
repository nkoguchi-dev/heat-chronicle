import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, expect, it, vi } from 'vitest';

import ErrorPage from '@/app/error';

describe('ErrorPage', () => {
  it('logs the error and offers a retry action', async () => {
    const error = new Error('failure');
    const reset = vi.fn();
    const consoleError = vi.spyOn(console, 'error').mockImplementation(() => undefined);
    const user = userEvent.setup();

    render(<ErrorPage error={error} reset={reset} />);

    expect(screen.getByRole('heading', { name: 'ページを表示できませんでした' })).toBeInTheDocument();
    expect(consoleError).toHaveBeenCalledWith('Unexpected page error:', error);
    await user.click(screen.getByRole('button', { name: '再試行' }));
    expect(reset).toHaveBeenCalledOnce();
  });
});
