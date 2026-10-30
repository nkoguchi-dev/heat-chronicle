# バックエンド開発環境の契約

現在の品質確認はローカルで実施します。本書のCI移行記述は導入当時の経緯です。現在の実行手順は[ローカル検証](./LOCAL_DEVELOPMENT.md#品質workflowを置き換えるローカル検証)を参照してください。

Issue #136の移行契約です。利用者向けAPI・データモデルは変えず、Python 3.14系のパッチ版を固定しません。
ホスト・CI・両imageのuv移行とDB専用Composeは実装済みです。下表は各段階の中間状態を残す移行順の記録です。
最終コードの結合結果と未実施範囲は[検証結果](./BACKEND_VERIFICATION.md)を参照してください。

## 責務と実行契約

| 経路 | 所有するもの | 接続・実行条件 |
| --- | --- | --- |
| uv | Python 3.14選択、backend/.venv、runtime/dev依存、uv.lock | PEP 621とPEP 735。requires-pythonは>=3.14,<3.15、.python-versionは3.14 |
| ホストFastAPI | reload、デバッグ、日常の品質検査 | backendからuv sync --locked、uv run --locked uvicorn app.main:app --reload --port 8000 |
| DynamoDB Local | ローカル開発の永続データ | Composeでhost 8001→container 8000、database/dataの既存bind mountを維持 |
| 開発用image | Linux上の開発依存とASGI互換性 | Python 3.14と同じuv.lock。必要時に独立build/runし、Composeの通常起動からは外す |
| Lambda用image | Linux/amd64のruntime依存とMangum handler | uv.lockのruntimeのみをtask rootへ導入。開発依存・uv本体は最終imageへ含めない |
| CI | locked環境の再現と品質ゲート | backend unit/integrationの既存check名とstrict型検査を維持 |

ホストのDYNAMODB_ENDPOINT_URLはhttp://127.0.0.1:8001、container内は明示したDynamoDB LocalのURLを使います。
endpointを設定した場合だけ既存のダミー資格情報を使い、未設定時はAWS SDKの通常の認証・endpoint解決を維持します。
localhostを本番の既定値へ変更しません。uv runはbackendをカレントに実行します。

## 初期化とデータの保護

ASGI lifespanで既存のtable作成とstation seed/migrationを実行します。
Lambdaは既存のimport時seedとlifespan offを維持し、CIの隔離handler smokeはseedをstub化します。

unitは外部DB・AWS・気象庁へ接続しません。integrationは専用DynamoDB Local endpointと専用table prefixを明示し、
開発用のprefixやデータをcleanup対象へ混ぜません。検証は既存database/dataへ触れない専用環境から始めます。
Compose停止・再起動・移行・切り戻しでdatabase/dataやvolumeを削除しません。
削除を伴うdown -v、volume prune、データディレクトリ削除を通常手順に含めません。

## 移行順と中間状態

| Issue | 変更 | マージ時点で維持する経路 |
| --- | --- | --- |
| #146 | 本契約を定義 | 現行Poetry/CI/Docker/Composeを変更しない |
| #147 | PEP 621/735、uv.lock、3.14選択とホスト用コマンド | 既存CI/Docker用に最小Poetry互換設定とlockを暫定維持 |
| #148 | ホストendpoint例、初期化、テスト分離と実接続確認 | Compose backendと既存AWS接続契約を維持 |
| #149 | 開発/Lambda imageの依存導入をuvへ変更 | CI用Poetry互換設定はまだ維持 |
| #150 | CIと依存更新の設定をuvへ変更 | 全consumer切替後にPoetry互換設定・lockを撤去 |
| #151 | ComposeをDynamoDB Localだけに限定 | ホストASGIと独立image buildを維持 |
| #152 | クリーン環境でhost/CI/Dockerを結合確認 | 未確認範囲と対象commitを記録 |

#147だけでPoetry互換資源を全削除すると、未移行CIとDockerが失敗します。
そのため完全撤去は#150のconsumer切替と同時に行います。依存定義の正本は標準metadataへ集約し、
暫定lockも既存版を保つためだけに更新します。無関係な依存更新・アプリ再配置を混ぜません。

## 品質確認と切り戻し

ホストとCIでblack→isort→flake8→mypy→unit/integrationを実行します。
開発imageでは実ASGIのhealthと主要API、Lambda imageでは外部接続を使わない代表eventを確認します。
本番用imageは既存のOS更新・最小context・脆弱性/秘密検査を維持します。
uvとimageでPython 3.14およびlocked依存を照合します。実AWSへの配備は移行の対象外です。

各段階の切り戻しは直前の正常なmain commitから通常PRを作成し、関係するconsumerとmetadata/lockを一組で戻します。
Poetry全撤去後に単一Dockerfileだけを旧方式へ戻しません。DBは同じbind mountを再利用し、再作成・消去しません。
本番のrelease/prodや稼働imageは変更せず、別途承認された配備・復旧手順を使います。

## 一次資料

- [uvのlockとsync](https://docs.astral.sh/uv/concepts/projects/sync/)
- [uvのDocker統合](https://docs.astral.sh/uv/guides/integration/docker/)
- [uvのLambda統合](https://docs.astral.sh/uv/guides/integration/aws-lambda/)
