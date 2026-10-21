# uvホスト開発移行の結合確認

Issue #152 / 親 #136。確認日は2026-10-21。
対象コードは公開main `dfacdc462f4134d8cf65d270c9bbd31d4c8cb669`です。
このcommitから新しいworktreeを作り、既存の.venv/.env.local/node_modulesをコピーせずに検証しました。
最終記録PRでは文書だけを変更し、そのPRとmerge後のCIはGitHubの各commitのchecksを正本とします。

## 環境と依存の一致

| 対象 | Pythonと依存 | 結果 |
| --- | --- | --- |
| macOS arm64のホスト | uv 0.12.0 / Python 3.14.6 / 新規.venv | sync --locked成功、73件導入 |
| 開発用Linux/amd64 image | Python 3.14.8 / uv.lockの全group | 実package集合・版73件が完全一致 |
| Lambda用Linux/amd64 image | Python 3.14.8 / uv.lockのruntime | 実package集合・版35件が完全一致 |
| CI | commit固定setup-uv、uv 0.12.0、Python 3.14 | PR/mainのfresh syncとunit/integration/image smoke成功 |

Python要件は>=3.14,<3.15、.python-versionは3.14です。上記パッチ版は実測値で、固定値ではありません。
移行前の75 package versionはuv.lockで全件維持しています。Windows専用等のmarkerにより導入件数は異なります。
uv audit --lockedは全75件の既知脆弱性・不利なstatusが0でした。auditコマンドのexperimental警告は残り、結果は確認時点のsnapshotです。
Poetry設定、poetry-core、poetry.lock、PoetryのCI install/cache/実行コマンドは撤去済みです。

## ホスト・DB・frontend

ComposeはDynamoDB Localだけを提供します。既存database/dataに触れない専用project-directoryとbind mountを、configで照合してから使いました。
検証portはDB 18151、host API 18152、frontend 30136です。host endpoint、test prefix、frontend origin/proxyを明示しました。

- up --waitでHealthy、sentinel保存→stop→再起動→同じ値を取得できました。
- 新worktreeのuvicorn --reloadで新しい専用prefixのtable3件を作成し、station seed/migrationが完了しました。
- health、都道府県、地点、気温cacheの4 APIが200でした。
- fixtureの気温2件と取得履歴を専用DBへ用意し、実frontend→Vite proxy→host API→DBをChromiumで確認しました。
- 東京の選択表示、気温種別変更、再読み込み、Canvasを確認し、HTTP/JavaScriptエラー0、外部/上流取得0でした。
- 新prefixの初期化とintegration cleanup後も、別tableの既存sentinel値は変わりませんでした。

このfixtureは実気象データの完全性や気象庁の実疎通を検証するものではありません。
初回の専用port試験では許可origin不一致を検出し、テスト環境のCORS_ALLOW_ORIGINSとproxyを合わせ、新browserで再確認しました。
既定手順はfrontend localhost:3000とhost API 127.0.0.1:8000で一致しています。

## 品質とimage

black、isort、flake8、mypyが成功し、unit 116件、専用test prefixのintegration 25件が成功しました。
unitのsocket禁止と、integrationの未指定/AWS endpoint/通常prefix拒否も確認済みです。
production用Docker/NginxのBrowser Smoke 4件が成功しました。

開発imageは[専用DB smoke](../tools/run-backend-development-smoke.sh)で初期化・seed・4 APIとcleanupを確認しました。
Lambdaはnetwork none・seed stubでhealthと都道府県APIが200、Python 3.14とuv/Poetry/dev tool/pip/ensurepip不在を確認しました。
ローカル未配備候補のmanifest digestは`sha256:c20f03130a51280a6fde77e3ab31f66ff57cc5fc9c970e6151f52bc37419a7ba`です。
これは稼働版の識別子ではありません。Trivy 0.76.0でHIGH/CRITICAL 0・秘密0、inventoryとSBOM生成を確認しました。
DB更新時刻は2026-10-20T19:12:26Z。UNKNOWN 1件は[Windows専用APIの指摘](https://pkg.go.dev/vuln/GO-2026-5024)で、Linux候補では非該当と判断し、findingは抑制していません。

## CIと文書

各実装PRで既存required checksと追加開発image/security checksが成功しました。
直前mainではCI Backend / Browser Smoke / Code Security / Secret Detection / Container Securityの5 workflowが成功しました。
Frontend quality checksは既存のPR実行で確認しました。
#150のmainではDependabotのuv /backend更新jobも成功し、uv ecosystemへの切替を確認しました。
README、root/backend AGENTS、backend README、レビューガイドはuvとDB専用Composeへ揃えました。
中間状態と切り戻しの判断は[開発環境の契約](./BACKEND_DEVELOPMENT.md)を参照してください。

## 未実施範囲

ECR push、本番Lambda更新、release/prod更新、Terraform apply、通知送信、本番サイトの変更後smokeは行っていません。
本番・実気象庁への負荷試験、データ削除・復旧試験、API/データモデルの変更も対象外です。
既存のローカルDBデータを移動・削除せず、検証専用container/networkと一時環境だけを終了処理の対象にします。
