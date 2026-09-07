'use client';

import { createContext, useContext, type ReactNode } from 'react';

import type { Clock } from '@/features/shared/domain/clock';

const ClockContext = createContext<Clock | null>(null);

interface ClockProviderProps {
  clock: Clock;
  children: ReactNode;
}

export function ClockProvider({ clock, children }: ClockProviderProps): React.JSX.Element {
  return <ClockContext.Provider value={clock}>{children}</ClockContext.Provider>;
}

export function useClock(): Clock {
  const clock = useContext(ClockContext);
  if (clock === null) throw new Error('useClock requires a ClockProvider');
  return clock;
}
