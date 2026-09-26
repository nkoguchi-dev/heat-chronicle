# frontend

Vite + Reactによる静的SPAです。バックエンドAPIから取得した気温データをCanvas 2Dでヒートマップとして描画します。

## 構成

- Vite / React 19 / TypeScript / Tailwind CSS v4
- shadcn/ui (Radix UI) / Canvas 2D API
- `index.html`、`src/main.tsx`、`src/App.tsx`: metadata、React root、Provider、error boundary、画面の接続
- `src/features/heatmap/`: ヒートマップの画面、Hook、表示、データ変換
- `src/features/shared/`: 複数機能で共有するContext、API client、時計
- `src/components/ui/`: UIプリミティブ

コード規約と品質検査は[AGENTS.md](./AGENTS.md)を参照してください。

## ホストでの開発

ComposeはDynamoDB LocalとFastAPIを起動します。frontendはホストで実行してください。

```bash
docker compose up
```

別のターミナルで:

```bash
cd frontend
npm ci
npm run dev
```

画面は`http://localhost:3000`です。ブラウザーは同じoriginの`/api`へ接続し、Viteが`http://127.0.0.1:8000`のFastAPIへ転送します。別のAPI originへ転送するときは`HEAT_CHRONICLE_API_PROXY_TARGET`を指定します。`npm run preview`でも同じproxyを使います。

## 本番buildと配信

`VITE_API_URL`には公開APIのHTTP(S) originを指定します。path、認証情報、query、fragmentは含めません。値はbuild時にブラウザー向けbundleへ埋め込まれるため、機密情報を渡さないでください。

```bash
VITE_API_URL=https://api.example.com npm run build
npm run preview
```

静的成果物は`dist/`です。`release/prod`のデプロイワークフローは既存S3 bucketへ同期し、CloudFrontを無効化します。production用Docker/Nginxは同じ成果物のBrowser Smokeに使用します。

```bash
sh tools/run-browser-smoke.sh
```

Browser SmokeはPlaywrightの固定API応答を使い、実API・AWSには接続しません。失敗時は`frontend/test-results/`と`frontend/playwright-report/`を確認してください。
