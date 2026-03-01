# Frontend CLAUDE.md

フロントエンド（Next.js / TypeScript）の開発ガイドです。

## 開発コマンド

`frontend/` ディレクトリで実行してください。

```bash
npm install       # 依存関係インストール
npm run dev       # 開発サーバー起動（ポート 3000）
npm run build     # 本番ビルド（静的エクスポート）
npm run lint      # ESLint
```

## ディレクトリ構成の原則

| ディレクトリ | 役割 |
|------------|------|
| `src/app/` | Next.js App Router（ページ・レイアウト） |
| `src/features/` | 機能単位のモジュール（components, lib を内包） |
| `src/components/ui/` | shadcn/ui プリミティブ（Radix UI） |
| `src/hooks/` | カスタムフック |
| `src/types/` | TypeScript 型定義（バックエンド API 対応） |
| `src/lib/` | 汎用ユーティリティ |

## 命名規則

| 対象 | 規則 | 例 |
|------|------|-----|
| コンポーネントファイル | PascalCase.tsx | `Heatmap.tsx`, `ColorLegend.tsx` |
| ユーティリティファイル | kebab-case.ts | `color-scale.ts`, `api-client.ts` |
| フックファイル | use-xxx-xxx.ts（kebab-case） | `use-temperature-data.ts` |
| 型定義ファイル | kebab-case.ts | `api.ts` |
| 変数・関数 | camelCase | `fetchStations`, `colorScale` |
| 型・インターフェース | PascalCase | `Station`, `TemperatureRecord` |
| コンポーネント | PascalCase | `StationSelector`, `ProgressBar` |

## コーディングスタイル

- インデント: 2 スペース
- クォート: ダブルクォート
- セミコロン: あり
- パスエイリアス: `@/*` → `./src/*`
- ESLint: next/core-web-vitals + typescript
- スタイリング: Tailwind CSS v4
- UI コンポーネント: shadcn/ui（new-york スタイル）

## データフロー

1. ページ読み込み時に URL パラメータ（`?pref=&station=`）から地点を特定
2. REST API で地点一覧を取得し、セレクタに表示
3. 選択された地点のキャッシュ済みデータを API から取得
4. 未取得の月がある場合、`/api/temperature/{id}/fetch-month` を順次呼び出し
5. データが届くたびにヒートマップを Canvas 上に逐次描画

## API クライアント

`src/features/shared/libs/api-client.ts` の fetch ラッパーを使用してバックエンドと通信します。直接 `fetch` を呼び出さず、必ずこのクライアント経由でリクエストしてください。

## 環境変数

| 変数名 | 説明 |
|--------|------|
| `NEXT_PUBLIC_API_URL` | バックエンド API の URL（ローカル開発時: `http://localhost:8000`） |
