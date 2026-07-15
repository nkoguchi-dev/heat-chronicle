import { render, renderHook, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import type { ReactNode } from 'react';
import { describe, expect, it, vi } from 'vitest';

import { ThemeToggle } from '@/features/shared/components/ThemeToggle';
import { ThemeProvider, useTheme } from '@/features/shared/contexts/theme-context';

interface WrapperProps {
  children: ReactNode;
}

function Wrapper({ children }: WrapperProps): React.JSX.Element {
  return <ThemeProvider>{children}</ThemeProvider>;
}

describe('ThemeProvider', () => {
  it('uses the stored theme and synchronizes the root class', () => {
    localStorage.setItem('theme', 'dark');

    const { result } = renderHook(() => useTheme(), { wrapper: Wrapper });

    expect(result.current.theme).toBe('dark');
    expect(document.documentElement).toHaveClass('dark');
  });

  it('falls back to the system preference', () => {
    const mediaQuery: MediaQueryList = {
      matches: true,
      media: '(prefers-color-scheme: dark)',
      onchange: null,
      addListener: vi.fn(),
      removeListener: vi.fn(),
      addEventListener: vi.fn(),
      removeEventListener: vi.fn(),
      dispatchEvent: vi.fn(),
    };
    vi.mocked(window.matchMedia).mockReturnValue(mediaQuery);

    const { result } = renderHook(() => useTheme(), { wrapper: Wrapper });

    expect(result.current.theme).toBe('dark');
  });

  it('toggles the theme through the accessible control', async () => {
    vi.mocked(window.matchMedia).mockReturnValue({
      matches: false,
      media: '(prefers-color-scheme: dark)',
      onchange: null,
      addListener: vi.fn(),
      removeListener: vi.fn(),
      addEventListener: vi.fn(),
      removeEventListener: vi.fn(),
      dispatchEvent: vi.fn(),
    });
    const user = userEvent.setup();
    render(
      <ThemeProvider>
        <ThemeToggle />
      </ThemeProvider>,
    );

    const toggle = screen.getByRole('button', { name: 'ダークモードに切り替え' });
    await user.click(toggle);

    expect(localStorage.getItem('theme')).toBe('dark');
    expect(screen.getByRole('button', { name: 'ライトモードに切り替え' })).toBeInTheDocument();
  });

  it('throws when the hook is used outside the provider', () => {
    vi.spyOn(console, 'error').mockImplementation(() => undefined);

    expect(() => renderHook(() => useTheme())).toThrow('useTheme must be used within a ThemeProvider');
  });
});
