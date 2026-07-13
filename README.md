# Heat Chronicle

日本全国 979 か所の気象観測地点から、日別の最高・最低・平均気温を選び、長期的な変化を
年×日付のヒートマップで比較できるWebアプリケーションです。

[公開サイトを見る](https://heat-chronicle.koppepan.org/?pref=44&station=4) ・
[ソースコードを見る](https://github.com/nkoguchi-dev/heat-chronicle)

![東京の最高気温を50年分表示したHeat Chronicleの画面](./docs/images/heat-chronicle.jpg)

気象庁の「過去の気象データ検索」から必要な年月だけを取得し、DynamoDBへキャッシュします。
長期間の大量データを扱いながら、外部サイトへの負荷と利用者の待ち時間を抑えることを
テーマに、フロントエンド、API、データ取得、AWSインフラ、CI/CDまで個人で設計・実装しました。

## 技術的な見どころ

### Canvasによる長期データの可視化

- 1年を横一列、1日を1セルとして、数十年分の日別気温をCanvas 2D APIで描画
- DOM要素を日数分生成せず、長期間でも描画負荷とメモリ使用量を抑制
- 最高・最低・平均気温の切り替え、日付と気温のツールチップ、ライト／ダークテーマに対応

### 50年単位の段階取得

- 初回表示は最大50年に限定し、古い期間は「さらに過去50年分を読み込む」操作で追加
- キャッシュ済みデータを先に描画し、未取得の月だけを順次取得して画面へ反映
- 地点変更時は進行中のリクエストを中断し、古いレスポンスによる表示の競合を防止

### DynamoDBキャッシュと鮮度管理

- `daily-temperature` に日別データ、`fetch-log` に地点・年月ごとの取得日時を保存
- 確定済みの過去年月は再取得せず、当月など更新される可能性があるデータだけを24時間後に再取得
- パーティションキーとソートキーによる期間クエリで、対象地点・期間のデータだけを取得

### 外部サイトに配慮したデータ取得

- 気象庁へのリクエスト間隔を2秒以上に制御
- HTTPエラー時は最大3回、指数バックオフでリトライ
- 1リクエストを1か月分に限定し、取得済み年月への重複アクセスを抑制

### AWS上のサーバーレス構成とIaC

- フロントエンドはNext.jsの静的エクスポートをS3 + CloudFrontで配信
- FastAPIをコンテナ化し、Mangum経由でAWS Lambda + API Gateway上に配置
- AWSとGitHub ActionsのリソースをTerraformで管理し、SOPS + ageでtfvarsを暗号化
- GitHub ActionsからAWSへはOIDCで認証し、長期アクセスキーを使用しない

### 継続的な品質管理

- バックエンドはpytestによるユニットテストと、DynamoDB Localを使うAPI統合テストを分離
- Black、isort、Flake8、mypyの静的チェックをCIで実行
- フロントエンドはESLint、TypeScript、本番ビルドをCIで検証
- PRでは共通・バックエンド・フロントエンド・インフラ別のレビューガイドをClaude PR Reviewから参照

## 担当範囲

個人開発として、以下の工程を一貫して担当しています。

- 要件整理、画面・API・データモデルの設計
- Next.js / Reactによるフロントエンド実装
- FastAPIによるAPIとレイヤードアーキテクチャの実装
- 気象庁データの取得、解析、キャッシュ鮮度管理
- DynamoDBのテーブル・アクセスパターン設計
- TerraformによるAWS / GitHubリソースのコード化
- GitHub Actionsによるテスト、ビルド、デプロイの自動化
- テスト、レビューガイド、運用ドキュメントの整備

## 設計上の判断とトレードオフ

| 判断 | 採用理由 | トレードオフ |
|---|---|---|
| ヒートマップをCanvasで描画 | 数万セルを少ないDOM要素で描画できる | セル単位のアクセシビリティやレスポンシブ制御を別途設計する必要がある |
| 50年ごとの段階取得 | 初回応答とデータ量を抑え、必要な利用者だけが古い期間を取得できる | 全期間を一度に比較するには追加操作が必要になる |
| オンデマンド取得 + DynamoDBキャッシュ | 事前収集の運用コストを抑え、閲覧された地点からデータを蓄積できる | 初回閲覧ではスクレイピング完了まで待ち時間が発生する |
| 静的フロントエンド + Lambda API | 常時稼働サーバーを持たず、小規模サービスの運用負荷を抑えられる | Lambdaの実行時間やコールドスタートを考慮する必要がある |
| 気象庁HTMLのスクレイピング | 公開画面から必要な過去データを取得できる | HTML変更への追従と、アクセス頻度への慎重な配慮が必要になる |

## AIを利用した開発プロセス

このプロジェクトはAI機能を提供するプロダクトではなく、AIをソフトウェア開発工程へ
組み込む実践例です。

- [`AGENTS.md`](./AGENTS.md) と各レイヤーのガイドに、アーキテクチャ、依存方向、品質基準を明文化
- [`docs/REVIEW_GUIDE.md`](./docs/REVIEW_GUIDE.md) を起点に、変更領域別のチェック項目を整備
- GitHub ActionsのClaude PR Reviewが差分とレビューガイドを読み、PRへフィードバック
- AIの提案は自動採用せず、既存設計との整合性を確認し、lint・型検査・テスト・ビルドで検証

## アーキテクチャ

```text
┌─────────────────────┐      ┌────────────────────────┐
│ Next.js / Canvas    │─────▶│ API Gateway            │
│ S3 + CloudFront     │ HTTPS│ FastAPI on AWS Lambda  │
└─────────────────────┘      └───────────┬────────────┘
                                         │
                              ┌──────────▼──────────┐
                              │ DynamoDB            │
                              │ data + fetch log    │
                              └──────────┬──────────┘
                                         │ 未取得・要更新の月だけ
                              ┌──────────▼──────────┐
                              │ 気象庁              │
                              │ 過去の気象データ検索 │
                              └─────────────────────┘
```

## 技術スタック

| レイヤー | 技術 |
|---|---|
| フロントエンド | Next.js 16 / React 19 / TypeScript / Tailwind CSS v4 / Canvas 2D API |
| バックエンド | Python 3.12 / FastAPI / Pydantic / httpx / BeautifulSoup4 / Mangum |
| データストア | Amazon DynamoDB / DynamoDB Local |
| インフラ | AWS Lambda / API Gateway / ECR / S3 / CloudFront / Route 53 / Terraform |
| CI/CD | GitHub Actions / AWS OIDC / Claude PR Review |
| 品質管理 | pytest / moto / Black / isort / Flake8 / mypy / ESLint / TypeScript |

## ディレクトリ構成

```text
heat-chronicle/
├── backend/           # FastAPI、ドメインロジック、DynamoDB、スクレイパー
├── frontend/          # Next.js、Canvasヒートマップ、UI
├── infrastructure/    # AWS / GitHub Terraform
├── database/          # DynamoDB Localのデータ
├── docs/              # PRレビューガイド、運用・改善ドキュメント
├── scripts/           # 地点マスタ生成、デプロイ補助
├── .github/workflows/ # CI、デプロイ、Claude PR Review
├── compose.yaml       # ローカル開発環境
└── AGENTS.md          # AIエージェント向け開発ガイド
```

## ローカル開発

前提: Docker / Docker Compose、Python 3.12 + Poetry、Node.js 22 + npm

```bash
# DynamoDB Local、バックエンド、フロントエンドをまとめて起動
docker compose up
```

個別の開発コマンドと設計ルールは、[`backend/AGENTS.md`](./backend/AGENTS.md) と
[`frontend/AGENTS.md`](./frontend/AGENTS.md) を参照してください。

## CI/CD

PRでは変更領域に応じたCIを実行し、`release/prod` ブランチへのpushでAWSへデプロイします。

- フロントエンド: `npm ci` → ESLint → 静的ビルド → S3同期 → CloudFrontキャッシュ無効化
- バックエンド: 静的解析・ユニットテスト・統合テスト → Docker build → ECR push → Lambda更新

## データ出典

気象データは[気象庁ホームページ](https://www.data.jma.go.jp/)「過去の気象データ検索」から
取得しています。本サービスは個人開発プロジェクトです。
