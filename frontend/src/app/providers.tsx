'use client';

import type { ReactNode } from 'react';
import { ThemeProvider } from '@/features/shared/contexts/theme-context';

interface ProvidersProps {
  children: ReactNode;
}

export function Providers({ children }: ProvidersProps): React.JSX.Element {
  return <ThemeProvider>{children}</ThemeProvider>;
}
