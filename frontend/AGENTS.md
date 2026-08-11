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

フィーチャー内では、実装対象が存在するディレクトリだけを作成します。空のディレクトリや、将来利用するためだけのレイヤーは作りません。

| 配置先        | 責務                                                                                          |
| ------------- | --------------------------------------------------------------------------------------------- |
| `page.tsx`    | Hookと主要コンポーネントを組み合わせ、画面全体のデータフローを接続するcomposition root        |
| `components/` | フィーチャー固有の表示と利用者操作を担当するReactコンポーネント                               |
| `hooks/`      | フィーチャー固有の状態、副作用、API操作、URL・ブラウザAPIとの同期をカプセル化するカスタムHook |
| `libs/`       | 検証、変換、データ結合、表示文言へのマッピングなどReactに依存しない純粋ロジック               |
| `types/`      | ドメイン型、画面状態、Hookの入出力など複数ファイルで利用する型                                |

## アーキテクチャ原則

- `src/app/**/page.tsx` はルーティングの責務に限定し、画面実装を `src/features/[feature]/page.tsx` から読み込む
- `src/features/[feature]/page.tsx` はcomposition rootとし、Hookの呼び出し、イベントの接続、主要コンポーネントの配置に集中させる。API呼び出し、Effectの詳細、純粋な変換、型定義、汎用的な子コンポーネントを同じファイルへ実装しない
- フィーチャー固有のコンポーネント、Hooks、ユーティリティ、型定義は、そのフィーチャーの `components/`、`hooks/`、`libs/`、`types/` に配置する
- 各フィーチャーは自己完結させ、別フィーチャーの内部コードを直接importしない
- 複数機能で利用するコードのみ `src/features/shared/` に配置し、機能間で共有する場合はこの層を経由する
- `src/components/ui/` には機能固有のロジックを持たせない
- `src/components/ui/` のshadcn/ui生成コードは、生成元との差分を避けるため、アプリ固有のファイル命名・Props宣言・カバレッジ規約の対象外とする。ただしlintと型チェックは必須とする
- 現在の要件と責務の境界に基づいて分割し、単なる行数削減、1か所からしか呼ばない自明な処理、将来の再利用予測だけを理由に抽象化しない
- 状態、イベント、ブラウザAPIを利用する静的SPAであるため、`'use client'`の使用自体やClient Componentの数を制限しない。静的exportとS3・CloudFront配信を維持できる境界を優先する

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
- コンポーネント、Hook、公開関数と重要なコールバックは、引数と戻り値の型を明示する
- 型アサーションとnon-null assertionは、事前の検証や不変条件によって実行時の安全性を説明できる場合だけ使用する
- Optionalな値はoptional chainingとnullish coalescingを使って安全に扱い、`null`と`undefined`の意味を混同しない
- マジックナンバーと、複数箇所で意味を共有する固定文字列は名前付き定数へ置き換える
- ネストが深くなる場合は早期returnや処理の分割で平坦化する
- コメントは処理内容の言い換えではなく、判断理由、外部仕様、直感的でない制約を説明する
- スタイリング: Tailwind CSS v4
- UIコンポーネント: shadcn/ui（new-yorkスタイル）は選択肢の一つとし、新規UIでの利用を必須にしない
- Canvasのcomputed寸法やtooltip位置など、実行時の値をCSSへ渡すinline styleは、理由が明確な場合に使用できる

## テスト

- Vitest、React Testing Library、jsdomを使用する
- 新規・変更されたロジックには正常系、異常系、境界値のテストを追加する
- コンポーネントは実装詳細ではなく、表示、アクセシブルな名前、ユーザー操作を検証する
- APIやブラウザAPI、タイマーはテストごとにリセットし、テスト間の依存を作らない
- アプリ固有コードのカバレッジ閾値はlines / statements / functions 80%、branches 75%を維持する
- `src/components/ui/` のshadcn/ui生成コード、型定義、App Routerの薄い配線はカバレッジ対象外とする
- 仕様または受け入れ条件を変更した場合は、Markdown仕様書、Gherkin、Unit、Integration、Component、Browser Smokeの更新要否を同じPull Requestで判断する
- Gherkin全件をBrowser Smokeへ重複実装しない。テスト層の選択は `docs/TESTING_STRATEGY.md` を正本とする
- Browser Smoke導入後は、production静的配信、直接アクセス、再読み込み、履歴、キーボード操作、主要導線をそこで確認し、境界値や詳細な異常系はUnit、Integration、Componentテストを優先する

## 状態管理

- URL、APIレスポンス、React stateのどれを正本とするかを状態ごとに明確にし、同じ状態を複数箇所で独立して保持しない
- 再読み込み、共有、戻る・進む操作で復元すべき地点と気温種別はURLを正本とする
- APIから取得した観測地点と気温データはAPIレスポンスを基に管理し、別のstateへ意味の同じデータを複製しない
- ローディング、進捗、選択中の一時状態などURLやAPIへ永続化しないUI状態はReact stateで管理する

## APIアクセス

- `src/features/shared/libs/api-client.ts` のfetchラッパーを使用し、コンポーネントやHookから直接`fetch`を呼び出さない
- HTTP通信と共通のレスポンス・エラー処理はAPIクライアントに集約する
- 機能固有のAPI操作は `src/features/[feature]/hooks/` のカスタムHookにカプセル化する
- APIのリクエストとレスポンスには明示的なTypeScript型を定義する
- APIレスポンスは外部入力として扱い、`null`、欠損、想定外の値を安全に処理する
- 再実行、選択変更、アンマウントで不要になったリクエストを中断し、古いレスポンスで新しい結果を上書きしない
- 意図しない再取得と重複リクエストを避け、同一操作の多重実行が必要かを明示する
- 気象庁データの月別取得は2秒間隔で逐次実行し、この間隔を短縮したり無制御に並列化したりしない
- コンポーネントはHTTPエラーの詳細ではなく、ローディングやエラー表示などUI上の状態を扱う

## エラーとローディング

- APIエラーを握りつぶさず、開発者向けログとユーザー向け表示を適切に扱う
- 入力不正、ネットワーク障害、一時的なサーバー障害、リソース未検出、中断を可能な範囲で区別し、中断を利用者向けエラーとして表示しない
- API通信中はローディング状態を表示する
- 処理中の重複操作が問題になるコントロールは無効化する
- エラーメッセージには、再試行などユーザーが次に取れる行動を含める
- ページ全体の致命的なエラーはNext.jsの `error.tsx` で扱う

## 静的エクスポート

- `next.config.ts`の`output: 'export'`を維持し、production buildで`frontend/out`を生成する
- S3とCloudFrontから静的成果物を配信し、実行時のNode.jsサーバー、SSR、Server Actionsを必要とする機能を導入しない
- 実行時に決まるIDは動的ルートではなくクエリパラメータで受け渡す
- `useSearchParams()` を使用するコンポーネントは `Suspense` でラップし、ユーザーが状態を理解できるfallbackを指定する
- ルーティング、URLパラメータ、Client Component境界を変更した場合は `npm run build` で静的エクスポートを確認する

## セキュリティ

- APIキー、アクセストークン、パスワードなどの機密情報をリポジトリやクライアントコードへ含めない
- `NEXT_PUBLIC_`が付く環境変数はブラウザへ公開される前提で扱い、機密情報を設定しない
- `dangerouslySetInnerHTML`は使用しない。避けられない場合は、理由、入力元、サニタイズ方法をPull Requestへ記録する
- 外部リンクを新しいタブで開く場合は`noopener noreferrer`相当の対策を行う
- 外部から取得したURLをリンクや画像に使う場合は、許可するスキームと用途を確認する

## アクセシビリティ

- 見出し、ランドマーク、フォーム、ボタン、リンク、エラー表示には意味に合ったHTML要素とアクセシブルな名前を使用する
- 主要操作をキーボードだけで完了でき、フォーカス位置を認識できるようにする
- ローディング、エラー、結果更新などの重要な状態変化を支援技術へ伝え、色だけで状態や意味を表現しない
- Canvasヒートマップは最大200年程度の気温を色で俯瞰する視覚的な時系列探索を目的とするため、セル単位の文字ラベル、個別フォーカス、スクリーンリーダー向け代替一覧は要件にしない

## Canvas描画

- 最大200年程度の気温データを扱うため、データ、表示範囲、寸法など描画結果に関係する値が変わった場合だけCanvasを再描画する
- 描画処理の変更では、不要な再描画、DOM要素の大量生成、全データの重複変換がないことを確認する

## データフロー

1. ページ読み込み時にURLパラメータ（`?pref=&station=`）から地点を特定
2. REST APIで地点一覧を取得し、セレクタに表示
3. 選択された地点のキャッシュ済みデータをAPIから取得
4. 未取得の月がある場合、`/api/temperature/{id}/fetch-month` を順次呼び出し
5. データが届くたびにヒートマップをCanvas上に逐次描画

## 新規フィーチャーの追加

1. `src/features/[feature]/` を作成し、Hookと主要コンポーネントを接続するcomposition rootを `page.tsx` に置く
2. 実装対象がある場合だけ `components/`、`hooks/`、`libs/`、`types/` を作成し、責務に応じてコードを分ける
3. `src/app/` にルートを追加し、フィーチャーのページコンポーネントを読み込む
4. 共有が必要になったコードだけを `src/features/shared/` に移す
5. 品質チェックをすべて実行する

## 環境変数

| 変数名                | 説明                                                            |
| --------------------- | --------------------------------------------------------------- |
| `NEXT_PUBLIC_API_URL` | バックエンドAPIのURL（ローカル開発時: `http://localhost:8000`） |

- `NEXT_PUBLIC_` が付く値はブラウザへ公開されるため、機密情報を含めない

## AI生成コード

- AIが生成または提案したコード、テスト、仕様にも、人が書いた変更と同じ規約と検証基準を適用する
- 未使用の抽象化、既存規約との不整合、存在しないAPI、誤った型、根拠のない依存追加がないかを、既存仕様、一次資料、実行結果で確認する
- 内容と採用理由を説明できない変更をそのまま採用しない

## 品質チェック

変更後は次の順序で実行し、警告・エラーを解消してください。

```bash
npm run format:check
npm run lint
npm run typecheck
npm run test:coverage
npm run build
```
