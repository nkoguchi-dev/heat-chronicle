# ローカル開発コマンドの契約

Issue #138の技術契約です。#161は契約、#162はMakefileとプロセス管理、#163は契約の自動検査・実動作・利用手順を所有します。
#135と#136のホスト実行を前提に、#137の内部再配置に先行します。ASGI入口`app.main:app`を利用し、Port／Adapter構成を変更しません。

## targetと正規コマンド

rootでGNU Make、Docker Compose、uv 0.12.0、Node.js 24とnpmを使います。Pythonはbackendの3.14指定をuvが解決し、patchは固定しません。OSのツール導入は行いません。

| target | 委譲先と成功条件 | 失敗・停止後の状態 |
| --- | --- | --- |
| `setup` | backendの`uv sync --locked`、frontendの`npm ci`。backend/.env.localが無い場合だけ.env.exampleをコピー。両依存導入完了で成功 | 最初の失敗で停止。途中までの依存導入は残り、再実行可能。既存設定を上書きしない |
| `dev` | `docker compose up -d --wait dynamodb-local`後、backendの`uv run --locked uvicorn app.main:app --reload --host 127.0.0.1 --port 8000`とfrontendの`npm run dev`を並行監視。両HTTP入口の準備完了を表示 | Ctrl+C、起動途中失敗、どちらかの終了で所有する両ホストprocess groupを子孫まで終了。DBは残す |
| `stop` | `docker compose stop dynamodb-local`。未起動・停止済みでも成功 | DB停止だけ。bind mountとデータを保持。ホストはdevのCtrl+Cで止める |
| `check` | backendのblack --check → isort --check-only → flake8 → mypy → unit → 専用prefixのintegration、frontendのformat:check → lint → typecheck → test:coverage → build | 最初の失敗を返す。integrationのためDBを起動し、終了後も保持。formatを自動修正しない |
| `browser-smoke` | `sh tools/run-browser-smoke.sh`。既存のproduction Docker/NginxとPlaywright固定API応答 | 既存scriptが自身の一時containerを回収。trace/reportの所在を維持 |

Makeは入口であり、個別コマンドもデバッグの正規経路として維持します。target間の暗黙のsetupやdev起動はありません。
`make -j`で複数targetを同時実行せず、別worktreeでも既定のDB名・portを共有するため同時起動しません。

## 起動・停止と入力

1. setupで依存と初回設定を準備します。既存.env.localは内容・mtimeを保持し、空ファイルやsymlinkも上書きしません。
2. devはbackendの有効設定を読み、HTTP loopbackかつ明示portのDB endpoint、localまたはlocal-で始まるprefixを検査します。AWS endpointやendpoint未設定ではDB操作前に停止します。
3. Compose health完了後にホストを起動します。FastAPIのlifespanが既存のtable作成・station seed/migrationを行い、その完了後の/healthとViteの/を待ちます。初期化を別scriptで二重実行しません。
4. 既定はDB127.0.0.1:8001、API127.0.0.1:8000、画面localhost:3000です。検証用API/frontend portは環境変数で変更し、proxyとCORSも同じ値へ合わせます。Viteは同一originの/apiを利用します。
5. 占有portは起動前に拒否し、他のプロセスは停止しません。待機には期限を設け、子プロセスが早期終了した場合も直ちに失敗します。
6. dev終了時は自身が開始したprocess groupへ終了signalを送り、猶予後も残る場合だけ強制終了し、waitで回収します。DBは成功・失敗どちらでもstopまで維持します。

親runnerはCtrl+Cで130、TERMで143、子の異常終了は非0を返します。子が予期せず0で終了した場合も失敗です。GNU Make自体はrecipe失敗を通常2へ変換するため、shellで観測するmakeの終了コードとrunnerの終了コードは区別します。
コマンド名・作業ディレクトリと子の標準出力/標準エラーを表示し、pipeで失敗を隠しません。ログに環境変数全体を出しません。

## データと検証

`database/data`の既存bind mountを維持します。stopや失敗cleanupへvolume削除、データ削除、pruneを含めません。
integrationは既存ガードに従う専用test-prefixを強制し、開発用local prefixをcleanup対象にしません。
make checkとbackend CIではtoolsのformat/import/lint/typecheckと契約・POSIXライフサイクル検査も実行します。
frontendの検査buildはCI同様の固定ローカルAPI originを渡し、AWSや本番への接続を必要としません。

#163ではMakeのtarget・委譲・危険な削除操作を検査します。専用fixtureで既存設定保護、正常起動、Ctrl+C、各ホストの起動失敗・実行中終了、待機失敗、終了コード、孫プロセス回収を検証します。
新規worktreeでsetup/check/browser-smokeを実行し、専用bind mountのsentinelをstop・再起動後に照合します。既存利用者のdatabase/dataを検証fixtureとして使いません。

個別の規則は[backendガイド](../backend/AGENTS.md)、[frontendガイド](../frontend/AGENTS.md)、[バックエンド契約](./BACKEND_DEVELOPMENT.md)を参照してください。

## 実装の入力

`make setup`の後に`make dev`を実行します。macOS/LinuxのPOSIX process groupを使用します。Windowsでの実行は契約に含めません。
検証や既存portの回避には`HEAT_DEV_API_PORT`、`HEAT_DEV_FRONTEND_PORT`を指定します。既定は8000/3000で、launcherがproxyとCORSを同じ値へ合わせます。
DBの設定はbackendの.env.localと通常の環境変数優先順位をそのまま使います。Composeの標準入力`COMPOSE_FILE`/`COMPOSE_PROJECT_NAME`も利用可能ですが、DB endpointはComposeの公開portと一致させてください。
`make check`のintegrationは`test-make`prefixを使用します。同じDBへ複数worktreeから同時にcheckを実行しないでください。
`make browser-smoke`のportは既存の`E2E_PORT`で変更できます。失敗時はfrontend/test-resultsとfrontend/playwright-reportを確認します。

## 初回構築から日常操作

1. rootで`make setup`を実行します。backend/.env.localが既にある場合は上書きしないため、endpointがhttp://127.0.0.1:8001、prefixがlocalまたはlocal-*であることを確認します。
2. `make dev`を実行し、Readyの表示を待ちます。http://localhost:3000へアクセスします。APIだけなら`curl --fail http://127.0.0.1:8000/health`で確認できます。
3. Ctrl+CでFastAPI・Viteを停止します。DBを止めるなら`make stop`を実行します。もう一度stopしてもデータは消えません。再開は`make dev`です。
4. 変更後は`make check`、配信確認は`make browser-smoke`を実行します。後者はChromium導入済みを前提とし、未導入ならfrontendで`npx playwright install chromium`を実行します。

各コマンドは前景のstdout/stderrへログを出します。必要ならターミナルのログ保存を使い、pipeを使う場合は元コマンドの終了コードを保持してください。
失敗した品質検査は表示されたcwdとコマンドをそのまま再実行できます。Makeは最初の失敗で止まります。
起動失敗では、DBの状況を`docker compose ps`/`docker compose logs dynamodb-local`で確認します。FastAPIのtable/seed失敗はbackendの起動ログ、Viteの失敗はfrontendの起動ログへ出ます。ポート占有時は利用中のプロセスを確認し、自分の環境だけを停止するか専用portを選んでください。

```sh
HEAT_DEV_API_PORT=18000 HEAT_DEV_FRONTEND_PORT=13000 make dev
# 個別にbackendを調べる場合（backendカレント）
uv run --locked uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
# 個別にfrontendを調べる場合（frontendカレント）
npm run dev
# Make契約の検査だけを実行する場合（backendカレント）
uv run --locked pytest ../tools/tests/ -v
```

手動で起動したホストプロセスの停止は、そのターミナルのCtrl+Cで行います。make stopは他のターミナルのプロセスを探して終了しません。

初回構築・反復停止・異常終了・CIの検証範囲は[確認記録](./LOCAL_DEVELOPMENT_VERIFICATION.md)を参照してください。
