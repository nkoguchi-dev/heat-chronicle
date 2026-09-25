'use client';

import { AppErrorFallback } from '@/app/AppErrorFallback';

interface ErrorPageProps {
  error: Error & { digest?: string };
  reset: () => void;
}

export default function ErrorPage({ error, reset }: ErrorPageProps): React.JSX.Element {
  return <AppErrorFallback error={error} reset={reset} />;
}
