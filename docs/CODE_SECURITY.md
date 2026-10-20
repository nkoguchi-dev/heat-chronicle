# コードセキュリティ検査

Semgrep Community EditionでPython・JavaScript/TypeScriptの危険なパターンを検出します。
依存脆弱性・秘密情報・コンテナ検査とは別の検査です。

## 構成と判定

- Semgrep 1.181.0をPython 3.12の独立環境で実行します。
- ルールは`tools/security/config.json`の固定commitからsecurity配下を選択します。
- PR・main・日次・手動で全対象を解析し、metricsとversion checkを無効化します。
- Semgrep AppSec Platformへソースを送らず、AWS資格情報・復号鍵・アプリsecretを使いません。
- 未分類指摘はINFOを含め失敗。部分解析・言語未解析・版不一致も失敗にします。
- テスト用の既知操作やparser非対応箇所はconfigのテスト除外範囲で管理します。
- 誤検出は`exceptions.json`でrule/path/code hash/理由/所有者/期限を限定します。
  例外が消滅・変更・期限切れでも失敗します。ルール全体の抑制やnosemgrepは使いません。

Actions「Code Security」は件数のみのsummary.jsonを7日間公開保存します。
未加工JSON・SARIF・scanner.logは公開artifactへ保存しません。
失敗の詳細は同じcommit・固定版でローカル再現し、所有者専用領域で確認します。
未評価の実脆弱性は非公開の報告経路で評価し、公開Issueへ詳細を自動転載しません。
既存required checksの名前・Rulesetは変更しません。

## ローカル再現

リポジトリrootから実行します。出力先は公開・Git管理対象外の専用ディレクトリにします。

```sh
python3.12 -m venv /private/tmp/heat-security-venv
/private/tmp/heat-security-venv/bin/pip install -r tools/security/requirements.txt
git clone https://github.com/semgrep/semgrep-rules.git /private/tmp/heat-security-rules
git -C /private/tmp/heat-security-rules checkout 17e31e11ebac99fb7dfe1cd288f7a32151b6f3f9
SECURITY_RULES_DIR=/private/tmp/heat-security-rules /private/tmp/heat-security-venv/bin/python -m unittest discover -s tools/security/tests -v
/private/tmp/heat-security-venv/bin/python tools/security/scan.py --rules-dir /private/tmp/heat-security-rules --output-dir /private/tmp/heat-security-report
```

更新時は本体・config・workflowの版を同期し、fixture・全体解析・既存例外を再確認します。
[Semgrep CLI](https://semgrep.dev/docs/cli-reference)と
[ルールのライセンス](https://semgrep.dev/legal/rules-license)を参照してください。
