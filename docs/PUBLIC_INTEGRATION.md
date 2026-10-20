# 公開開発への統合範囲（Issue #216）

公開mainの依存更新を基点に、別管理で検証した実装と継続検査を移植します。
履歴のmergeや非公開branchのpushを行わず、公開mainに新しい変更として記録します。

## 含める内容

- API容量・CORS・アクセスログ・通知relayの定義と単体/mockテスト。
- OIDCのrelease ref限定、ECR取得policy、実行ロールの最小権限、静的配信のresponse headers。
- OS更新と不要installer除去を含むLambda用image、コード・秘密情報・コンテナ検査。
- 未使用shadcn CLIの削除と必要なCSS/MIT告知の保持。

公開側のPoetry lockとprod AWS provider lockは維持します。
npmも残る全packageのversion/resolved/integrityを維持し、不要な217 lock entryだけを除きます。

## 公開しない内容と運用境界

非公開Git履歴、実環境の監査・検証証跡、実通知先、個人用の本番SOPS入力は移植しません。
既存の公開AWS暗号文も最新運用入力として誤使用しないよう追跡対象から外します。
過去に公開済みの履歴は書き換えません。
本番入力は所有者が非公開領域で維持し、[実行手順](../infrastructure/docs/sops-encryption-guide.md)のHEAT_PROD_TFVARSで指定します。
backend bucket/keyを維持し、同じ資源を複数のTerraform rootから適用しません。

公開Actionsには検査summaryだけを保存し、未加工SAST結果・コンテナfindings/SBOMは公開artifactへ出しません。
詳細調査は同じsourceと固定scannerでローカル再現します。

mainへの統合は本番反映ではありません。release/prodへのpush、配備workflow実行、AWS apply、通知送信は別途扱います。
未完了の費用メール到達確認と停止・復旧検証は既存の非公開運用課題に残し、この統合で完了扱いにしません。
uv移行はこの統合の後、公開Issue #136で進めます。

## 統合時の検証（2026-10-21）

backendのformat/import/lint/typecheckとunit 110件、専用in-memory DynamoDB integration 25件が成功しました。
frontendのformat/lint/typecheck、119件とcoverage閾値、production build、全依存audit 0件、Docker/Nginx Browser Smoke 4件が成功しました。
Terraform fmt/validate、prod mock 13件・容量fixture mock 1件、relay unit 12件・probe unit 3件が成功しました。
コード検査437ルールは解析エラー0・未分類0・限定した既存例外7件、秘密検査はstaged/公開履歴とも検出0件です。
検査自身の正負fixtureも実行しました。

Linux/amd64の完成imageで隔離handler smoke、TrivyのHIGH/CRITICAL 0・秘密0とSBOM生成を確認しました。
UNKNOWN 1件のCVE-2026-39824は[Go公式DB](https://pkg.go.dev/vuln/GO-2026-5024)が示すWindows専用APIの指摘で、
Linux候補では非該当と判断しました。finding自体は抑制していません。今後の別imageへ判断を自動継承しません。

所有者入力をpipeで渡した既存prod stateに対する通常planは終了0・managed差分なしでした。
refreshではAPI stageのdeployment_idとLambdaのimage/code/更新時刻に既存stateとの差がありましたが、
自動配備のcomputed属性とignore_changes対象で、今回のコードからAWS更新は計画されませんでした。
state保存・AWS apply・image配備・通知送信は実施していません。
公開CIの結果は対応PRのchecksを正本とし、これらのローカル結果と区別します。
