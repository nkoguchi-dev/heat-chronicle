import type { Clock } from '@/features/shared/domain/clock';

export class SystemClock implements Clock {
  now(): Date {
    return new Date();
  }
}
