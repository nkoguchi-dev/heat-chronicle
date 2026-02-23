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

## データフロー

1. ページ読み込み時に URL パラメータ（`?pref=&station=`）から地点を特定
2. REST API で地点一覧を取得し、セレクタに表示
3. 選択された地点のキャッシュ済みデータを API から取得
4. 未取得の月がある場合、`/api/temperature/{id}/fetch-month` を順次呼び出し
5. データが届くたびにヒートマップを Canvas 上に逐次描画

## 開発コマンド

```bash
# 依存関係インストール
npm install

# 開発サーバー起動（ポート 3000）
npm run dev

# 本番ビルド（静的エクスポート）
npm run build

# Lint
npm run lint
```

## ビルドと配信

本番環境では `next build` で静的 HTML/JS/CSS にエクスポートし（`out/` ディレクトリ）、S3 + CloudFront で配信しています。
