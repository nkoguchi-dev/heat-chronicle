# 秘密情報の検査と漏洩対応

Gitleaks 8.30.1でstaged差分と到達可能な全Git履歴を検査します。
公式archiveのSHA-256を`tools/secrets/version.json`へ固定し、導入時に照合します。
`.gitleaks.toml`は既定ルールにDiscord Webhookとage秘密鍵を追加します。
完全なage公開recipient形式に限る誤検出例外を持ち、秘密鍵やファイル全体は除外しません。

## ローカルとデプロイ前

```sh
python3 tools/secrets/install.py --bin-dir "${XDG_CACHE_HOME:-$HOME/.cache}/heat-chronicle-tools/gitleaks-8.30.1"
git config --show-origin --get core.hooksPath
# 既存hookと統合し、上書きしないことを確認した後だけ設定する。
git config --local core.hooksPath .githooks
bash tools/secrets/scan.sh history
```

pre-commitはstaged差分、pre-pushは到達可能履歴を確認します。バイナリ未配置・版違いでも失敗します。
各デプロイの「Deployment security」ジョブは完全履歴を取得し、shallowなら失敗させます。検査成功前にAWS権限を持つ配備ジョブへ進みません。
baseline・allow comment・ignore fileで検出を隠しません。
公開Actionsへ出すのは件数とrule/file/line/commitのsummaryだけで、値・Match・Author・Emailは保存しません。
raw reportはローカルの所有者専用一時領域で扱い、不要になったら削除します。

GitHub側のsecret scanning/push protectionは現在の実設定を別途確認します。
ローカルhookは回避可能で、デプロイ前検査はpush後のため、サーバ側拒否と同じ保証にはしません。
未知形式・難読化・ignore対象の平文・dangling object・未取得refs・Issue/PR・既存artifactは別の確認対象です。
通常検査ではSOPSを復号しません。検査成功を過去の漏洩不存在の証明にはしません。

## 検出時

1. commit/pushを止め、credentialかと露出場所・時刻・権限を安全な環境で確認します。
2. 実credentialなら発行元で速やかに失効・ローテーションし、不正利用を調査します。
3. Webhookは所有する秘密入力とSSMを同期し、古い値が使えず新しい値で動くことを確認します。
4. age鍵の交換だけでは過去に共有した暗号文を守れないため、復号可能な中のcredentialも調べます。
5. 調査・復旧・残余リスクは非公開の運用記録へ残します。履歴削除だけで対応を終えません。

実credentialを検証API・Issue・CLI引数へ貼りません。検査fixtureは未発行の合成文字列だけを使います。
[GitHub secret scanning](https://docs.github.com/en/code-security/concepts/secret-security/about-alerts)と
[Gitleaks固定版](https://github.com/gitleaks/gitleaks/tree/v8.30.1)を参照してください。
