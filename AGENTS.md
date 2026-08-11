# AGENTS.md

Codex（OpenAI）がこのリポジトリで作業する際のガイドです。

## プロジェクト概要

heat-chronicle は気象庁が公開している過去の気象観測データを取得・解析し、日別の最高・最低・平均気温をヒートマップとして可視化する Web アプリケーションです。プロジェクト全体の構成と設計上の判断は [README.md](./README.md) を参照してください。

## サブ AGENTS.md

各サブディレクトリに専用のガイドがあります。

- [backend/AGENTS.md](./backend/AGENTS.md) — バックエンド（Python / FastAPI）の開発コマンド・アーキテクチャ・コーディング規約
- [frontend/AGENTS.md](./frontend/AGENTS.md) — フロントエンド（Next.js / TypeScript）の開発コマンド・命名規則・コーディング規約

## 作業フロー

- すべての変更をGitHub Issueに紐づける。対応するIssueがない場合は、ファイルを変更する前にIssueを作成する
- 目的、スコープ、対象外、完了条件はIssueを正本とし、作業中に範囲が変わる場合はIssueを更新するか後続Issueを作成する
- 作業を開始する前に最新の `origin/main` を取得し、必ず `origin/main` を基点に作業ブランチを作成する。`main` 上で直接作業しない
- ブランチ名は `<type>/issue-<issue-id>/<title>` 形式の小文字ケバブケースとする。`type`には`feat`、`fix`、`docs`、`test`、`refactor`、`chore`などを使用する
- 変更は意味のある単位にまとめ、こまめにコミットする
- `main` への変更の取り込みは必ずPRを作成して行う。PRには目的、主な変更、確認方法、`Closes #<issue-id>`または`Fixes #<issue-id>`を記載する。マージ後の適用や確認まで完了条件に含むIssueでは、自動closeを避けるため`Refs #<issue-id>`を使用する
- `main`は`Protect main` Rulesetで保護し、Pull Requestとfrontend、backend、Browser Smokeのrequired checksをGitHub側でも強制する。Rulesetは`infrastructure/github/`のTerraformを正本とし、通常はWeb UIで直接変更しない。自己ロックからの復旧時だけ[インフラ手順](./infrastructure/README.md)のbreak-glassを使用し、復旧後にTerraformへ再同期する
- coding agentへIssueを指定した場合、Issueの範囲に対する実装、検証、commit、push、PR作成、自己レビューコメントまでを担当範囲とする
- PR 作成後に [`docs/REVIEW_GUIDE.md`](./docs/REVIEW_GUIDE.md) と変更領域に対応するレビューガイドを使って自己レビューし、結果を PR コメントとして追加する
- 人が内容を確認するまでPRをマージせず、自動マージを有効にしない。coding agentの自己レビューは人による確認を置き換えない
- マージ後はmainのGitHub Actionsを確認する。問題が見つかった場合はmainを直接修正せず、新しいIssueから通常のPRフローで対応する
- 作業のためにローカルブランチや Git worktree を作成した場合は、作業終了時に未コミットの変更がないことを確認し、作成した worktree とローカルブランチを削除する

## 仕様書の作成と更新

仕様関連文書は、次の責務に分けて管理する。

1. `docs/specs/**/*.md`: 利用者から見える目的、状態、操作、振る舞い、提供範囲、制約の正本
2. `docs/specs/**/*.feature`: 合意済み仕様を、利用者の操作と観測可能な結果で表す受け入れ条件
3. 技術資料: API、ライブラリ、内部構造など、実装に依存する契約と判断の根拠

- Markdown仕様書には、APIフィールド、HTTPステータス、関数、型、コンポーネント、状態管理などの実装依存情報を原則として含めない
- Gherkinの各ScenarioとScenario Outlineには、主要導線の`@smoke`または境界・異常系を含む`@regression`を付ける
- 仕様変更では、関連するMarkdown仕様書、Gherkin、技術資料、テストの更新要否を同じPRで確認する
- 仕様関連文書を変更したPRでは、[`docs/REVIEW_GUIDE_SPECS.md`](./docs/REVIEW_GUIDE_SPECS.md)に沿って自己レビューする
- テスト層の選択は[`docs/TESTING_STRATEGY.md`](./docs/TESTING_STRATEGY.md)を正本とする

## フルスタック起動

```bash
docker compose up                   # 全サービス起動（DynamoDB Local + Backend + Frontend）
docker compose up dynamodb-local    # DynamoDB Local のみ起動
```

## データベース（DynamoDB）

3 つのテーブルを使用しています。

| テーブル | PK | 説明 |
|---------|-----|------|
| `stations` | id（GSI: prec_no-index） | 気象観測地点マスタ |
| `daily-temperature` | station_id + date | 日別気温レコード |
| `fetch-log` | station_id + year_month | 取得済み年月の管理 |

## コード品質基準

### 共通ルール

- 実装前に既存コードのパターンを確認し、一貫性を保つ
- 問題が発生した場合は表面的な対処ではなく根本原因を分析する
- 不要なコードや未使用のインポートを残さない

### バックエンド品質チェック順序

```
black → isort → flake8 → mypy → pytest
```

### フロントエンド品質チェック

```
npm run format:check → npm run lint → npm run typecheck → npm run test:coverage → npm run build
```

Browser Smokeに関係する変更は、上記に加えてリポジトリルートで次を実行する。

```bash
sh tools/run-browser-smoke.sh
```

失敗時は`frontend/test-results/`のtrace・screenshotと`frontend/playwright-report/`のHTML reportを確認する。
この決定的な固定応答テストは、後述の実AWS・実API・実データを使う本番手動確認を置き換えない。

## 本番環境の動作確認

デプロイ後はブラウザで本番サイトにアクセスし、次のスモークテストを実施する。

- 東京都の東京を選択し、気温データをエラーなく表示できることを確認する
- 「〜1977年のデータを読み込む」などの過去データ読み込みボタンを繰り返しクリックし、1872年からのデータをエラーなく表示できることを確認する
- 次の各観測地点へ切り替え、エラーが発生しないことを確認する。これらの地点では過去データの読み込みは確認対象外とする
  - 石狩地方 — 札幌
  - 宮城県 — 仙台
  - 愛知県 — 名古屋
  - 大阪府 — 大阪
  - 福岡県 — 福岡
  - 沖縄県 — 那覇

> [!NOTE]
> 沖縄県は地点数が多く、那覇が選択肢の表示領域外にある場合がある。那覇を確認するときは、地点一覧をスクロールして那覇を表示領域内に移動してからクリックする。

## 開発のベストプラクティス

- **パターン確認**: 新しいコードを書く前に、同種の既存実装を確認して同じパターンに従う
- **根本原因分析**: エラーが出たら表面的な修正ではなく、なぜ起きたかを調査する
- **一貫性の保持**: 命名規則・ディレクトリ構成・エラーハンドリングを既存コードと揃える
- **最小限の変更**: 依頼された内容に直接関係する変更のみ行う
