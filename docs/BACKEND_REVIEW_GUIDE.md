# バックエンド PR レビューガイド

> **前提**: 本ガイドはバックエンド固有の観点をまとめたものです。
> 全体共通の観点（コード品質、セキュリティ、環境変数、テスト品質等）は
> [PR レビューガイド（全体共通）](./REVIEW_GUIDE.md) を参照してください。

このドキュメントは、バックエンドの PR をレビューする際のチェック観点をまとめたものです。
Codex による実装・レビューで使用します。

---

## 1. レイヤードアーキテクチャ

### レイヤーの依存方向

- [ ] 依存の方向が内側に向かっているか（Presentation → Application → Domain ← Infrastructure）
- [ ] Application 層が Domain 層以外のプロジェク内レイヤーを import していないか
- [ ] Infrastructure 層が Application / Presentation / DI を import していないか
- [ ] Presentation 層が Infrastructure を直接呼び出していないか
- [ ] Domain 層が外部ライブラリや他レイヤーに依存していないか
- [ ] Domain Model、業務ルール、Repository / Port がドメインリソース単位のディレクトリに整理されているか
- [ ] Presentation 層の知識（HTTP ステータスコード、`Request`/`Response` オブジェクト等）が Application 層に漏れていないか
- [ ] Domain 層に Presentation / Infrastructure の DTO が置かれていないか
- [ ] UseCase が Presentation 層へ Domain Model を直接返さず、ユースケース専用の Output DTO に変換しているか
- [ ] Application 専用 DTO のフィールドに Domain Model を使い回していないか
- [ ] 形が同じだけの DTO をレイヤー・ユースケース・エンドポイント間で使い回していないか

### UseCase / Service パターン

- [ ] UseCase が機能単位のディレクトリに整理されているか
- [ ] UseCase クラスが `GetStationUseCase`、ファイルが `get_station_use_case.py` のように命名されているか
- [ ] 1つの UseCase クラスが1つのユースケースの実行に集中しているか（HTTP 知識を持たない）
- [ ] Presentation 層から呼び出せる公開メソッドが1つの UseCase クラスにつき1つ以下になっているか
- [ ] 複数の UseCase から呼び出される処理が `application/shared/` の Service に分離され、Presentation 層から直接呼び出されていないか
- [ ] 複数の責務を 1 つの UseCase または Service に詰め込んでいないか
- [ ] 補助的なロジックはプライベートメソッド（`_` プレフィックス）になっているか

### リポジトリパターン

- [ ] DynamoDB へのアクセスが Infrastructure 層（Repository）に閉じているか
- [ ] Repository / 外部 I/O のインターフェースが Domain 層に `Protocol` として定義されているか
- [ ] Application 層や Presentation 層から DynamoDB クライアントを直接操作していないか

### 依存性注入（DI）

- [ ] FastAPI の `Depends` を使った DI になっているか（Presentation には UseCase の型エイリアスを注入）
- [ ] コンストラクタや関数内で外部依存を直接生成（インスタンス化）していないか

## 2. FastAPI 固有

- [ ] エンドポイントのレスポンスモデルが `response_model` で明示されているか
- [ ] Request / Response DTO が Presentation 層に専用の Pydantic Model として定義されているか
- [ ] Presentation 層の API リソースがディレクトリ化され、各エンドポイントが 1 ファイルに分離されているか
- [ ] Presentation DTO が原則 `strict=True`, `extra="forbid"` で外部入出力を厳密に検証しているか
- [ ] `HTTPException` のステータスコードが適切か（404 / 400 / 422 / 500 の使い分け）
- [ ] 500 エラーを返す際に `logger.error(..., exc_info=True)` でログが記録されているか
- [ ] 例外の握りつぶし（`except: pass`）がないか
- [ ] ビジネスロジック上の例外と予期しない例外が適切に分離されているか

## 3. DynamoDB アクセス

- [ ] DynamoDB 操作（`put_item`, `get_item`, `query`, `scan` 等）が Infrastructure 層（Repository）に閉じているか
- [ ] `scan` の乱用がないか（フルスキャンを避け `query` を優先する）
- [ ] `query` の際に適切な `KeyConditionExpression` が指定されているか
- [ ] ページネーション（`LastEvaluatedKey`）が実装されているか（大量レコードを返す可能性がある場合）
- [ ] テーブル名が環境変数やコンフィグ経由で管理されているか（ハードコードしない）
- [ ] GSI（グローバルセカンダリインデックス）を適切に活用しているか（`prec_no-index` 等）
- [ ] DynamoDB Item やファイル入力が Infrastructure 専用の strict Pydantic DTO で検証されているか
- [ ] Read / Write など用途の異なる外部 DTO を、形が同じという理由で使い回していないか

## 4. 気象庁データ取得・解析

- [ ] 気象庁へのリクエストが `JmaClient` 経由で行われているか（直接 `httpx` を使わない）
- [ ] レート制限（2 秒インターバル）を回避または短縮する実装になっていないか
- [ ] 取得済み年月の管理に `fetch-log` テーブルが使用されているか
- [ ] パース処理が Infrastructure 層に閉じているか（HTML 解析ロジックを上位レイヤーに漏らさない）

## 5. テスト

### ユニットテスト（pytest）

- [ ] Domain 層・Application 層のビジネスロジックにユニットテストがあるか
- [ ] テストが外部依存なしで実行できるか（DynamoDB・JmaClient をモック化している）
- [ ] 新規・変更された機能に対するテストが追加されているか

### DynamoDB テスト（moto）

- [ ] DynamoDB を使う Repository のテストに `moto` が使用されているか
- [ ] テスト前にテーブルの作成・クリーンアップが行われているか
- [ ] テストが他のテストに依存せず独立して実行できるか

## 6. コード品質チェック

以下のコマンドが全て通ることを確認する:

```bash
black --check .
isort --check-only .
flake8 .
mypy .
pytest
```

- [ ] `black` のフォーマットが適用されているか
- [ ] `isort` による import 順序が整理されているか
- [ ] `flake8` の警告・エラーがないか
- [ ] `mypy` の型チェックが通るか（`Any` の安易な使用がないか）
- [ ] `pytest` が全て通るか
