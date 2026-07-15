'use client';

import { Button } from '@/components/ui/button';

interface LoadMoreButtonProps {
  nextEndYear: number;
  onLoadMore: () => void;
}

export function LoadMoreButton({ nextEndYear, onLoadMore }: LoadMoreButtonProps): React.JSX.Element {
  return (
    <div className="flex w-full justify-center">
      <Button variant="outline" onClick={onLoadMore}>
        〜{nextEndYear}年のデータを読み込む
      </Button>
    </div>
  );
}
