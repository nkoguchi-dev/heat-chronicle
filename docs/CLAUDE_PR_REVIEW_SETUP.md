# Claude 自動 PR レビュー セットアップガイド

## 概要

PR が作成・更新されると、Claude が `docs/REVIEW_GUIDE.md`（および該当するレイヤー固有ガイド）に基づいて自動レビューを実行します。

### 作成されたワークフロー

| ファイル | トリガー | 用途 |
|---------|----------|------|
| `.github/workflows/claude-pr-review.yml` | PR の作成・更新 | 自動コードレビュー |
| `.github/workflows/claude-assistant.yml` | `@claude` メンション | 質問への回答・コード修正 |

---

## セットアップ手順

### 1. Anthropic API キーの設定

GitHub リポジトリの Settings > Secrets and variables > Actions から、以下のシークレットを追加します。

| シークレット名 | 値 |
|----------------|-----|
| `ANTHROPIC_API_KEY` | Anthropic の API キー（`sk-ant-...`） |

> API キーは [Anthropic Console](https://console.anthropic.com/) で発行できます。

### 2. GitHub Actions の権限設定

リポジトリの Settings > Actions > General > Workflow permissions で以下を設定します。

- **Read and write permissions** を選択
- **Allow GitHub Actions to create and approve pull requests** にチェック

### 3. ワークフローファイルのデプロイ

本リポジトリの `.github/workflows/` 配下に 2 つのワークフローファイルが追加されています。
`main` ブランチにマージされると自動的に有効になります。

---

## 動作の仕組み

### 自動レビュー（claude-pr-review.yml）

1. PR が作成または更新されると自動でトリガー（ドラフト PR は除外）
2. Claude が `gh pr diff` で差分を取得
3. `docs/REVIEW_GUIDE.md` を読み込み、全体共通のレビュー観点を把握
4. 変更ファイルに応じて `BACKEND_REVIEW_GUIDE.md` / `FRONTEND_REVIEW_GUIDE.md` も参照
5. コード上の具体的な問題にはインラインコメントを付与
6. 最後にサマリーコメント（総合評価 + チェック結果）を PR に投稿

### インタラクティブアシスタント（claude-assistant.yml）

PR のコメント欄で `@claude` と書くと、Claude が応答します。

```
@claude この関数のエラーハンドリングは適切ですか？
@claude このロジックをリファクタリングしてください
```

---

## レビュー出力の例

```markdown
## Claude PR Review

### 総合評価
軽微な指摘あり

### 確認した観点
- ✅ PR の粒度・コミットメッセージ
- ✅ レイヤードアーキテクチャの依存方向
- ✅ セキュリティ（機密情報のハードコード）
- ⚠️ 型安全性（一部 Any 型の使用）
- ⚠️ テスト（境界値テストの不足）

### 詳細
- `backend/app/services/temperature_service.py` L42: 戻り値の型が `Any` になっています。具体的な型を指定してください。
- `backend/tests/test_temperature.py`: 空のレスポンスケースのテストが不足しています。
```

---

## カスタマイズ

### レビュー観点の変更

レビューの観点を変更したい場合は、以下のファイルを編集します。

- `docs/REVIEW_GUIDE.md` — 全体共通
- `docs/BACKEND_REVIEW_GUIDE.md` — バックエンド固有
- `docs/FRONTEND_REVIEW_GUIDE.md` — フロントエンド固有

ワークフロー自体を変更する必要はなく、ガイドファイルの内容が反映されます。

### モデルの変更

`claude-pr-review.yml` の `claude_args` にモデル指定を追加できます。

```yaml
claude_args: |
  --max-turns 20
  --model claude-sonnet-4-5-20250929
  --allowedTools "..."
```

---

## トラブルシューティング

| 問題 | 対処 |
|------|------|
| ワークフローが実行されない | Actions タブで Workflow が有効か確認する |
| 権限エラーが出る | Workflow permissions が Read and write になっているか確認する |
| API エラーが出る | `ANTHROPIC_API_KEY` シークレットが正しく設定されているか確認する |
| レビューが途中で止まる | `--max-turns` の値を増やす |
