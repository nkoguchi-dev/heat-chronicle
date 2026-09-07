import type { ReactNode } from 'react';

import { ClockProvider } from '@/features/shared/contexts/clock-context';
import type { Clock } from '@/features/shared/domain/clock';

export class FixedClock implements Clock {
  constructor(private readonly instant: Date) {}

  now(): Date {
    return new Date(this.instant.getTime());
  }
}

export function createClockWrapper(clock: Clock): ({ children }: { children: ReactNode }) => React.JSX.Element {
  return function TestClockProvider({ children }: { children: ReactNode }): React.JSX.Element {
    return <ClockProvider clock={clock}>{children}</ClockProvider>;
  };
}
