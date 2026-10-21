# Makeによるローカル開発の検証

Issue #138の確認記録です。2026-10-21に、新規worktree（起点f040843）で依存・設定を作成し、検証コード6186d64で以下を確認しました。最終PRのチェックとマージ後main CIの結果はIssue #163/#138の完了コメントを参照してください。

## 環境と範囲

- macOS 27.0.1 arm64、GNU Make 3.81、uv 0.12.0、CPython 3.14.6、Node.js 24.21.0、npm 11.19.0、Docker Compose 5.4.0。
- backend/.venv、frontend/node_modules、backend/.env.localを既存worktreeからコピーせず、`make setup`で作成しました。
- Composeの標準override入力で専用container・network・専用の一時bind mountを使用しました。DBは127.0.0.1:18138、APIは18139、画面はlocalhost:30138、prefixはlocal-issue163です。
- 元のdatabase/dataと既存.env.localを変更していません。実AWS、気象庁の取得、本番配備は検証対象外であり、実施していません。

## 結果

| 確認 | 結果 |
| --- | --- |
| 新規setup | locked backend依存とnpm ciが成功。初回.env.local作成を確認 |
| setup反復 | 実コマンドとfixtureで既存ファイルの内容・mtimeを保持。空ファイルとdangling symlinkも保持 |
| setup失敗 | fixtureでuv sync失敗後に設定コピー・npm ciへ進まないことを確認 |
| dev | Compose health後に両ホストを起動し、ASGI lifespanのtable/seed完了とReady表示を確認 |
| HTTP | health、frontend、Vite proxy経由のprefecturesが200。既存の末尾slash redirectは追従して確認 |
| Ctrl+C | 実際のMake前景でrunnerが130を返し、uvicorn reload/worker/resource tracker、npm/Viteを含む記録済みの全所有PIDが消滅 |
| 異常終了 | 両ホストの起動失敗、実行中exit23、予期しないexit0、DB起動失敗、HTTP待機期限超過を実process fixtureで確認。実Vite起動コマンドへのexit17注入でもbackendと孫を回収 |
| stop・再起動 | stopを反復して成功。同じbind mountからdevを再起動し、sentinelの値と以前/current prefixのstation tableが残ることを照合 |
| check | format/import/lint/strict型検査、backend unit116件、integration25件、Make契約34件、frontend119件・coverage閾値・production buildが成功 |
| browser-smoke | makeからproduction Docker/Nginx + Playwrightへ委譲し、既存4件が成功 |
| Code Security | Semgrep 1.181.0・固定437ルールで未分類0、解析エラー0、既存を含む監査済み例外8。ローカルCLIの引数リスト実行1箇所はcode hashと理由・期限で限定 |

Make契約34件はDocker/実AWS/気象庁を使わず、所有するfixture内で実際の子・孫プロセスを起動します。
設定検査、Make委譲、検査順、データ削除を含めないこと、signalと失敗時の終了コード、全PID消滅を確認します。
修正後の全34件は、全体checkに続く追加2回の反復でも成功しました。
同じ検査を既存のBackend lint and unit testsジョブへ組み込み、required check名とRulesetを維持しています。

## 検証で修正した不具合

実行中のホストを異常終了させた反復試験で、macOSのkillpg(group, 0)がPermissionErrorとなり、元のexit23がcleanupの例外で上書きされました（Issue #230）。
[Apple XNUのkillpg1](https://github.com/apple-oss-distributions/xnu/blob/main/bsd/kern/kern_sig.c)ではzombieをgroupのsignal対象から除外し、対象なしの場合にEPERMを返す経路があります。
errnoだけでは生存プロセスへの権限不足と区別できないため、権限エラー時にpsのgroup/stateを確認します。空・zombieのみのgroupは終了済みとし、生存memberがいる場合の権限不足は失敗のままにしました。
両経路へ正負の回帰テストを追加し、実processの反復試験でも元の終了コードとPID回収を確認しました。

## 警告と未確認範囲

npm ciのfsevents install-scripts方針の通知、Vitestの既存performance案内、PlaywrightのNO_COLOR/FORCE_COLOR警告が出ました。allowScriptsや依存は変更しておらず、npm auditは0件、全検査は成功しています。
Browser Smokeの起動待機中にcurlの一時的な接続エラーが出ましたが、既存の待機ループが起動完了後に成功しました。
Windowsはprocess group契約に含めません。LinuxはPR/mainの既存backend CIで同じ契約検査を実行します。本番手動確認をローカル検証で代替したとは扱いません。

利用手順と入力・停止の契約は[ローカル開発](./LOCAL_DEVELOPMENT.md)を参照してください。
