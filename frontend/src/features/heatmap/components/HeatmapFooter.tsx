import { GitBranch } from 'lucide-react';

export function HeatmapFooter(): React.JSX.Element {
  return (
    <footer className="mt-auto flex flex-wrap items-center justify-center gap-x-3 gap-y-2 pt-8 text-xs text-muted-foreground">
      <span>
        データ出典:{' '}
        <a
          href="https://www.data.jma.go.jp/"
          target="_blank"
          rel="noopener noreferrer"
          className="underline underline-offset-4 transition-colors hover:text-foreground"
        >
          気象庁ホームページ
        </a>
      </span>
      <span aria-hidden="true" className="hidden text-border sm:inline">
        |
      </span>
      <a
        href="https://github.com/nkoguchi-dev/heat-chronicle"
        target="_blank"
        rel="noopener noreferrer"
        className="inline-flex items-center gap-1.5 font-medium text-foreground underline-offset-4 transition-colors hover:underline"
        aria-label="Heat ChronicleのソースコードをGitHubで開く（新しいタブ）"
      >
        <GitBranch aria-hidden="true" className="h-3.5 w-3.5" />
        GitHub
      </a>
    </footer>
  );
}
