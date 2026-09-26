import { describe, expect, it } from 'vitest';

import { cn } from '@/lib/utils';

describe('cn', () => {
  it('merges conditional and conflicting Tailwind classes', () => {
    const isHidden = false;
    expect(cn('px-2', isHidden && 'hidden', 'px-4')).toBe('px-4');
  });
});
