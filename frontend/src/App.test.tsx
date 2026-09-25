import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { afterEach, describe, expect, it, vi } from 'vitest';

import { App } from '@/App';

const testState = vi.hoisted(() => ({ shouldThrow: false }));

vi.mock('@/features/shared/infrastructure/system-clock', () => ({
  SystemClock: class {
    now(): Date {
      return new Date('2026-09-26T00:00:00+09:00');
    }
  },
}));

vi.mock('@/features/heatmap/page', async () => {
  const { useTheme } = await import('@/features/shared/contexts/theme-context');
  const { useClock } = await import('@/features/shared/contexts/clock-context');

  return {
    HeatmapPage: (): React.JSX.Element => {
      if (testState.shouldThrow) throw new Error('Vite entry failure');

      const clock = useClock();
      const { theme, toggleTheme } = useTheme();

      return (
        <section>
          <h1>Vite Heatmap</h1>
          <p>{clock.now().getFullYear()}</p>
          <button type="button" onClick={toggleTheme}>
            {theme}
          </button>
        </section>
      );
    },
  };
});

afterEach(() => {
  testState.shouldThrow = false;
});

describe('App', () => {
  it('connects the heatmap page to the clock and theme providers', async () => {
    const user = userEvent.setup();

    render(<App />);

    expect(screen.getByRole('heading', { name: 'Vite Heatmap' })).toBeInTheDocument();
    expect(screen.getByText('2026')).toBeInTheDocument();
    await user.click(screen.getByRole('button', { name: 'light' }));
    expect(screen.getByRole('button', { name: 'dark' })).toBeInTheDocument();
  });

  it('shows the application error fallback and retries rendering', async () => {
    testState.shouldThrow = true;
    const consoleError = vi.spyOn(console, 'error').mockImplementation(() => undefined);
    const user = userEvent.setup();

    render(<App />);

    expect(screen.getByRole('heading', { name: 'ページを表示できませんでした' })).toBeInTheDocument();
    expect(consoleError).toHaveBeenCalledWith('Unexpected page error:', expect.any(Error));

    testState.shouldThrow = false;
    await user.click(screen.getByRole('button', { name: '再試行' }));
    expect(screen.getByRole('heading', { name: 'Vite Heatmap' })).toBeInTheDocument();
  });
});
