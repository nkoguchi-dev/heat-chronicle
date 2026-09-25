# frontend

Next.js による SPA（シングルページアプリケーション）です。バックエンド API から取得した気温データを Canvas 2D でヒートマップとして描画します。

## 技術構成

- **Next.js 16** / **React 19** / **TypeScript**
- **Tailwind CSS v4** — スタイリング
- **shadcn/ui (Radix UI)** — UI コンポーネント
- **Canvas 2D API** — ヒートマップ描画

## ディレクトリ構成

```
frontend/src/
├── app/                              … Next.js App Router
│   ├── layout.tsx                    … ルートレイアウト
│   ├── page.tsx                      … メインページ
│   ├── providers.tsx                 … コンテキストプロバイダー
│   └── globals.css                   … グローバルスタイル
├── features/
│   ├── heatmap/                      … ヒートマップ機能
│   │   ├── components/
│   │   │   ├── Heatmap.tsx           … ヒートマップ本体（Canvas 描画）
│   │   │   ├── ColorLegend.tsx       … 凡例
│   │   │   ├── LoadingStatus.tsx     … 読み込み・進捗・エラー表示
│   │   │   └── StationSelector.tsx   … 地点選択 UI
│   │   └── lib/
│   │       ├── color-scale.ts        … 気温→色のマッピング
│   │       └── data-grid.ts          … データグリッド構築
│   └── shared/
│       ├── components/
│       │   └── theme-toggle.tsx      … ダーク/ライトテーマ切り替え
│       ├── contexts/
│       │   └── theme-context.tsx     … テーマ状態管理
│       └── libs/
│           └── api-client.ts         … API クライアント（fetch ラッパー）
├── components/ui/                    … shadcn/ui プリミティブ
├── hooks/
│   ├── use-temperature-data.ts       … 気温データ取得カスタムフック
│   ├── use-station-options.ts        … 都道府県・観測地点一覧取得カスタムフック
│   └── use-url-params.ts            … URL パラメータ管理
├── types/
│   └── api.ts                        … TypeScript 型定義（バックエンド API 対応）
└── lib/
    └── utils.ts                      … 汎用ユーティリティ
```

コーディング規約・開発コマンド・データフローの詳細は [AGENTS.md](./AGENTS.md) を参照してください。

Next.jsからViteへの段階移行で維持する実行・URL・API・配信の契約は、
[フロントエンドVite移行契約](../docs/frontend-vite-migration.md)を参照してください。

## ViteでのAPI接続

ホストでFastAPIを`http://127.0.0.1:8000`に起動し、`npm run dev:vite`で画面を起動します。
ブラウザーは同じoriginの`/api`へ接続し、ViteがFastAPIへ転送します。別のAPI originを使う場合は
`HEAT_CHRONICLE_API_PROXY_TARGET`を指定します。`npm run preview:vite`でも同じ転送設定を使います。

本番向けVite buildには公開API originを渡します。例:

```bash
VITE_API_URL=https://api.example.com npm run build:vite
```

`VITE_API_URL`はbuild時に静的成果物へ埋め込まれ、ブラウザーから`https://api.example.com/api/...`へ
接続します。設定できるのはHTTP(S) originのみで、認証情報やpathは含めません。
Next.js経路の`NEXT_PUBLIC_API_URL`は移行完了まで維持します。

## ビルドと配信

本番環境では `next build` で静的 HTML/JS/CSS にエクスポートし（`out/` ディレクトリ）、S3 + CloudFront で配信しています。
