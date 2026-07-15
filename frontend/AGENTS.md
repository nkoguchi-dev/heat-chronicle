# Frontend AGENTS.md

フロントエンド（Next.js / TypeScript）の開発ガイドです。

## 開発コマンド

`frontend/` ディレクトリで実行してください。

```bash
npm install             # 依存関係インストール
npm run dev             # 開発サーバー起動（ポート 3000）
npm run format          # Prettierでフォーマット
npm run format:check    # Prettierの適用確認
npm run lint            # ESLint
npm run typecheck       # TypeScript型チェック
npm run test            # Vitestを1回実行
npm run test:watch      # Vitestをwatchモードで実行
npm run test:coverage   # カバレッジ閾値を含めてテスト
npm run build           # 本番ビルド（静的エクスポート）
```

## ディレクトリ構成

フィーチャーベースの構成を採用します。

| ディレクトリ              | 役割                                                                           |
| ------------------------- | ------------------------------------------------------------------------------ |
| `src/app/`                | Next.js App Routerのルーティング、レイアウト、プロバイダー、エラーハンドリング |
| `src/features/[feature]/` | 機能単位の自己完結したモジュール（page, components, hooks, libs, types）       |
| `src/features/shared/`    | 複数機能で共有するコンポーネント、Hooks、Context、ユーティリティ               |
| `src/components/ui/`      | shadcn/uiプリミティブ（Radix UI）                                              |
| `src/lib/`                | shadcn/uiなどフレームワーク・UI基盤が利用する汎用ユーティリティ                |

## アーキテクチャ原則

- `src/app/**/page.tsx` はルーティングの責務に限定し、画面実装を `src/features/[feature]/page.tsx` から読み込む
- フィーチャー固有のコンポーネント、Hooks、ユーティリティ、型定義は、そのフィーチャーの `components/`、`hooks/`、`libs/`、`types/` に配置する
- 各フィーチャーは自己完結させ、別フィーチャーの内部コードを直接importしない
- 複数機能で利用するコードのみ `src/features/shared/` に配置し、機能間で共有する場合はこの層を経由する
- `src/components/ui/` には機能固有のロジックを持たせない
- `src/components/ui/` のshadcn/ui生成コードは、生成元との差分を避けるため、アプリ固有のファイル命名・Props宣言・カバレッジ規約の対象外とする。ただしlintと型チェックは必須とする

## 命名規則

| 対象                   | 規則                         | 例                                |
| ---------------------- | ---------------------------- | --------------------------------- |
| コンポーネントファイル | PascalCase.tsx               | `Heatmap.tsx`, `ColorLegend.tsx`  |
| ユーティリティファイル | kebab-case.ts                | `color-scale.ts`, `api-client.ts` |
| Hookファイル           | use-xxx-xxx.ts（kebab-case） | `use-temperature-data.ts`         |
| 型定義ファイル         | kebab-case.ts                | `api.ts`                          |
| 変数・関数             | camelCase                    | `fetchStations`, `colorScale`     |
| 定数                   | UPPER_SNAKE_CASE             | `TEMP_TYPE_LABELS`                |
| 型・インターフェース   | PascalCase                   | `Station`, `TemperatureRecord`    |
| コンポーネント         | PascalCase                   | `StationSelector`, `ProgressBar`  |

## コーディングスタイル

- インデント: 2スペース
- TypeScript / JavaScriptのクォート: シングルクォート
- セミコロン: あり
- 複数行の末尾カンマ: あり
- 1行の最大幅: 120文字
- フォーマット: Prettier
- パスエイリアス: `@/*` → `./src/*`
- ESLint: next/core-web-vitals + typescript + Prettier
- TypeScript: strictモードを維持し、`any`による型回避を行わない
- Propsは`interface`で定義する
- ネストが深くなる場合は早期returnや処理の分割で平坦化する
- スタイリング: Tailwind CSS v4
- UIコンポーネント: shadcn/ui（new-yorkスタイル）

## テスト

- Vitest、React Testing Library、jsdomを使用する
- 新規・変更されたロジックには正常系、異常系、境界値のテストを追加する
- コンポーネントは実装詳細ではなく、表示、アクセシブルな名前、ユーザー操作を検証する
- APIやブラウザAPI、タイマーはテストごとにリセットし、テスト間の依存を作らない
- アプリ固有コードのカバレッジ閾値はlines / statements / functions 80%、branches 75%を維持する
- `src/components/ui/` のshadcn/ui生成コード、型定義、App Routerの薄い配線はカバレッジ対象外とする

## APIアクセス

- `src/features/shared/libs/api-client.ts` のfetchラッパーを使用し、コンポーネントやHookから直接`fetch`を呼び出さない
- HTTP通信と共通のレスポンス・エラー処理はAPIクライアントに集約する
- 機能固有のAPI操作は `src/features/[feature]/hooks/` のカスタムHookにカプセル化する
- APIのリクエストとレスポンスには明示的なTypeScript型を定義する
- コンポーネントはHTTPエラーの詳細ではなく、ローディングやエラー表示などUI上の状態を扱う

## エラーとローディング

- APIエラーを握りつぶさず、開発者向けログとユーザー向け表示を適切に扱う
- API通信中はローディング状態を表示する
- 処理中の重複操作が問題になるコントロールは無効化する
- エラーメッセージには、再試行などユーザーが次に取れる行動を含める
- ページ全体の致命的なエラーはNext.jsの `error.tsx` で扱う

## 静的エクスポート

- 実行時に決まるIDは動的ルートではなくクエリパラメータで受け渡す
- `useSearchParams()` を使用するコンポーネントは `Suspense` でラップし、ユーザーが状態を理解できるfallbackを指定する
- ルーティングやURLパラメータを変更した場合は `npm run build` で静的エクスポートを確認する

## データフロー

1. ページ読み込み時にURLパラメータ（`?pref=&station=`）から地点を特定
2. REST APIで地点一覧を取得し、セレクタに表示
3. 選択された地点のキャッシュ済みデータをAPIから取得
4. 未取得の月がある場合、`/api/temperature/{id}/fetch-month` を順次呼び出し
5. データが届くたびにヒートマップをCanvas上に逐次描画

## 新規フィーチャーの追加

1. `src/features/[feature]/` を作成し、画面実装を `page.tsx` に置く
2. 機能固有のコードを `components/`、`hooks/`、`libs/`、`types/` に分ける
3. `src/app/` にルートを追加し、フィーチャーのページコンポーネントを読み込む
4. 共有が必要になったコードだけを `src/features/shared/` に移す
5. 品質チェックをすべて実行する

## 環境変数

| 変数名                | 説明                                                            |
| --------------------- | --------------------------------------------------------------- |
| `NEXT_PUBLIC_API_URL` | バックエンドAPIのURL（ローカル開発時: `http://localhost:8000`） |

- `NEXT_PUBLIC_` が付く値はブラウザへ公開されるため、機密情報を含めない

## 品質チェック

変更後は次の順序で実行し、警告・エラーを解消してください。

```bash
npm run format:check
npm run lint
npm run typecheck
npm run test:coverage
npm run build
```
