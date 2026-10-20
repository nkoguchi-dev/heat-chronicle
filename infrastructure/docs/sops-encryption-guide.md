# SOPS + age入力とTerraform

実入力は所有者の非公開領域で管理します。age秘密鍵、復号値、plan/state、Webhookは公開しません。
AWS prodの暗号化入力は公開ツリーへ置かず、`HEAT_PROD_TFVARS`へ絶対パスを設定します。
公開ツリーに残る過去の暗号文を最新の本番設定として使いません。

```sh
export SOPS_AGE_KEY_FILE="$HOME/.config/sops/age/keys.txt"
# HEAT_PROD_TFVARSには所有する非公開の最新暗号化入力の絶対パスを指定する。
# HEAT_PLANには所有者専用ディレクトリの保存planパスを指定する。
python3 infrastructure/aws/modules/backend_api/discord/package.py
terraform -chdir=infrastructure/aws/environments/prod plan -var-file=<(sops -d "${HEAT_PROD_TFVARS:?Set the owner-held production input}") -out="${HEAT_PLAN:?Set a protected plan path}"
# planの全差分をレビューし、本番操作の承認を得てから実行する。
terraform -chdir=infrastructure/aws/environments/prod apply -var-file=<(sops -d "${HEAT_PROD_TFVARS:?}") "${HEAT_PLAN:?}"
```

bash/zshで実行します。保存planにephemeral入力は保存されないのでapplyにも同じ入力を渡します。
URL変更時はdiscord_webhook_versionも増やします。通常sensitiveだけではstate保存を防げません。
変更前にAWS identity、backend bucket/key、provider lockと入力の所有元を照合し、別stateを作りません。

GitHub rootの暗号化設定は既存の所有元で管理し、AWS用入力と混ぜません。
SOPS入力の編集は`sops <暗号化入力パス>`を使い、復号をターミナルへ出しません。
age鍵の交換だけでは既に共有した過去の暗号文を守れないため、露出時は中のcredentialも評価します。
