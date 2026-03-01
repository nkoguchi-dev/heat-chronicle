# CLAUDE.md

Claude Code（claude.ai/code）がこのリポジトリで作業する際のガイドです。

## プロジェクト概要

heat-chronicle は気象庁の公開データをスクレイピングし、日別最高気温をヒートマップとして可視化する Web アプリケーションです。詳細仕様は SPEC.md を参照してください。

## サブ CLAUDE.md

各サブディレクトリに専用のガイドがあります。

- [backend/CLAUDE.md](./backend/CLAUDE.md) — バックエンド（Python / FastAPI）の開発コマンド・アーキテクチャ・コーディング規約
- [frontend/CLAUDE.md](./frontend/CLAUDE.md) — フロントエンド（Next.js / TypeScript）の開発コマンド・命名規則・コーディング規約

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
| `fetch-log` | station_id + year_month | スクレイピング済み年月の管理 |

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
npm run lint → npm run build
```

## 開発のベストプラクティス

- **パターン確認**: 新しいコードを書く前に、同種の既存実装を確認して同じパターンに従う
- **根本原因分析**: エラーが出たら表面的な修正ではなく、なぜ起きたかを調査する
- **一貫性の保持**: 命名規則・ディレクトリ構成・エラーハンドリングを既存コードと揃える
- **最小限の変更**: 依頼された内容に直接関係する変更のみ行う
