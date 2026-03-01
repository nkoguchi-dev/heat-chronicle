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
│   │   │   ├── ProgressBar.tsx       … データ取得プログレスバー
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
│   └── use-url-params.ts            … URL パラメータ管理
├── types/
│   └── api.ts                        … TypeScript 型定義（バックエンド API 対応）
└── lib/
    └── utils.ts                      … 汎用ユーティリティ
```

コーディング規約・開発コマンド・データフローの詳細は [CLAUDE.md](./CLAUDE.md) を参照してください。

## ビルドと配信

本番環境では `next build` で静的 HTML/JS/CSS にエクスポートし（`out/` ディレクトリ）、S3 + CloudFront で配信しています。
