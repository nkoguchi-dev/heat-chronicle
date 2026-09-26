import { ErrorBoundary } from '@/app/ErrorBoundary';
import { Providers } from '@/app/providers';
import { HeatmapPage } from '@/features/heatmap/page';

export function App(): React.JSX.Element {
  return (
    <ErrorBoundary>
      <Providers>
        <main className="min-h-screen bg-background">
          <HeatmapPage />
        </main>
      </Providers>
    </ErrorBoundary>
  );
}
