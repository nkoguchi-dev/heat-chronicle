'use client';

import type { ReactNode } from 'react';
import { ClockProvider } from '@/features/shared/contexts/clock-context';
import { SystemClock } from '@/features/shared/infrastructure/system-clock';

import { ThemeProvider } from '@/features/shared/contexts/theme-context';

const clock = new SystemClock();

interface ProvidersProps {
  children: ReactNode;
}

export function Providers({ children }: ProvidersProps): React.JSX.Element {
  return (
    <ClockProvider clock={clock}>
      <ThemeProvider>{children}</ThemeProvider>
    </ClockProvider>
  );
}
