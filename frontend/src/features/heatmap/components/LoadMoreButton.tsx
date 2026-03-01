"use client";

import { Loader2 } from "lucide-react";

import { Button } from "@/components/ui/button";

interface LoadMoreButtonProps {
  nextEndYear: number;
  loading: boolean;
  onLoadMore: () => void;
}

export function LoadMoreButton({
  nextEndYear,
  loading,
  onLoadMore,
}: LoadMoreButtonProps) {
  return (
    <div className="flex w-full justify-center">
      <Button
        variant="outline"
        onClick={onLoadMore}
        disabled={loading}
      >
        {loading ? (
          <>
            <Loader2 className="mr-2 h-4 w-4 animate-spin" />
            読み込み中...
          </>
        ) : (
          <>〜{nextEndYear}年のデータを読み込む</>
        )}
      </Button>
    </div>
  );
}
