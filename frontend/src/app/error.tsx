'use client';

import { useEffect } from 'react';

import { Button } from '@/components/ui/button';

interface ErrorPageProps {
  error: Error & { digest?: string };
  reset: () => void;
}

export default function ErrorPage({ error, reset }: ErrorPageProps) {
  useEffect(() => {
    console.error('Unexpected page error:', error);
  }, [error]);

  return (
    <main className="flex min-h-screen flex-col items-center justify-center gap-4 p-6 text-center">
      <h1 className="text-xl font-bold">ページを表示できませんでした</h1>
      <p className="text-sm text-muted-foreground">一時的な問題の可能性があります。もう一度お試しください。</p>
      <Button type="button" onClick={reset}>
        再試行
      </Button>
    </main>
  );
}
