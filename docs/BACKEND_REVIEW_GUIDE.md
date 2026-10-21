# バックエンド PR レビューガイド

> **前提**: 本ガイドはバックエンド固有の観点をまとめたものです。
> 全体共通の観点（コード品質、セキュリティ、環境変数、テスト品質等）は
> [PR レビューガイド（全体共通）](./REVIEW_GUIDE.md) を参照してください。

このドキュメントは、バックエンドの PR をレビューする際のチェック観点をまとめたものです。
Codex による実装・レビューで使用します。

---

## 1. Port／Adapterアーキテクチャ

[バックエンド設計](./BACKEND_ARCHITECTURE.md)の現在の構成を基準にする。全経路の移行が完了しており、旧Domain Port・DI具象型aliasへの例外を追加しない。

### レイヤーの依存方向

- [ ] 依存の方向が内側に向かっているか（Inbound Adapter → Inbound Port ← Use Case → Outbound Port ← Outbound Adapter）
- [ ] ApplicationがApplication内とDomain以外のプロジェクト内モジュールや外部frameworkをimportしていないか
- [ ] InfrastructureがApplicationのOutbound PortとDomainだけを内側の契約として参照し、Inbound Port / Use Case / Presentation / DIをimportしていないか
- [ ] PresentationがApplicationのInbound Portだけを参照し、Use Case具象 / Outbound Port / Domain / Infrastructure / DIに依存していないか
- [ ] Domain 層が外部ライブラリや他レイヤーに依存していないか
- [ ] Domain Modelと純粋な業務ルールがリソース単位に整理され、I/O PortはApplicationへ移されているか（Clock、FetchGuardを含む）
- [ ] Presentation 層の知識（HTTP ステータスコード、`Request`/`Response` オブジェクト等）が Application 層に漏れていないか
- [ ] Domain 層に Presentation / Infrastructure の DTO が置かれていないか
- [ ] UseCase が Presentation 層へ Domain Model を直接返さず、ユースケース専用の Output DTO に変換しているか
- [ ] Application 専用 DTO のフィールドに Domain Model を使い回していないか
- [ ] 形が同じだけの DTO をレイヤー・ユースケース・エンドポイント間で使い回していないか

### UseCase / Service パターン

- [ ] UseCase が機能単位のディレクトリに整理されているか
- [ ] UseCase クラスが `ListStationUseCase`、ファイルが `list_station_use_case.py` のように操作名を含めて命名されているか
- [ ] 1つの UseCase クラスが1つのユースケースの実行に集中しているか（HTTP 知識を持たない）
- [ ] Presentation 層から呼び出せる公開メソッドが1つの UseCase クラスにつき1つ以下になっているか
- [ ] 複数の UseCase から呼び出される処理が `application/shared/` の Service に分離され、Presentation 層から直接呼び出されていないか
- [ ] 複数の責務を 1 つの UseCase または Service に詰め込んでいないか
- [ ] 補助的なロジックはプライベートメソッド（`_` プレフィックス）になっているか

### リポジトリパターン

- [ ] DynamoDB へのアクセスが Infrastructure 層（Repository）に閉じているか
- [ ] Repository / Data Source / Clock / FetchGuardの契約がApplicationのOutbound Portに`Protocol`として定義されているか
- [ ] Application 層や Presentation 層から DynamoDB クライアントを直接操作していないか

### 依存性注入（DI）

- [ ] FastAPIの`Depends`がPresentation内のInbound Port型付き依存関数を指し、DIがproviderを登録しているか（具象型aliasのimportが残っていないか）
- [ ] Use Caseと具体Adapterの接続、外部client生成・終了の配線がComposition Rootに集約されているか
- [ ] main / Lambda handlerに業務処理や外部DTO変換がなく、ホストとLambdaの初期化契約が維持されているか
- [ ] 境界検査が絶対／相対importを検出し、移行の例外を増やしていないか

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
uv run --locked black --check .
uv run --locked isort --check-only .
uv run --locked flake8 .
uv run --locked mypy .
uv run --locked pytest
```

- [ ] `black` のフォーマットが適用されているか
- [ ] `isort` による import 順序が整理されているか
- [ ] `flake8` の警告・エラーがないか
- [ ] `mypy` の型チェックが通るか（`Any` の安易な使用がないか）
- [ ] `pytest` が全て通るか
