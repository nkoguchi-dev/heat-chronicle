# SOPS + age による terraform.tfvars 暗号化手順書

## 概要

このドキュメントでは、SOPS（Secrets OPerationS）と age 暗号化を使用して、`terraform.tfvars` を暗号化した `.tfvars.enc` ファイルを Git で管理する手順を説明します。

平文の `terraform.tfvars` は引き続き `.gitignore` で除外し、暗号化済みの `terraform.tfvars.enc` のみを Git にコミットします。Terraform 実行時はプロセス置換 `<(sops -d ...)` を使用するため、復号された内容がディスクに書き込まれることはありません。

### 対象ファイル

| 平文ファイル（Git 管理外） | 暗号化ファイル（Git 管理） | 機密情報 |
|---------|---------|---------|
| `infrastructure/github/terraform.tfvars` | `terraform.tfvars.enc` | Anthropic API キー |
| `infrastructure/aws/environments/prod/terraform.tfvars` | `terraform.tfvars.enc` | ドメイン名・リージョン等 |

### 前提条件

- macOS に `sops` と `age` がインストール済み（`brew install sops age`）
- age キーファイルが `~/.config/sops/age/keys.txt` に保存済み

---

## 1. 環境変数の設定

SOPS が秘密鍵を見つけられるように、シェルの設定ファイル（`.bashrc` / `.zshrc`）に以下を追加します。

```bash
export SOPS_AGE_KEY_FILE="$HOME/.config/sops/age/keys.txt"
```

設定を反映します。

```bash
source ~/.zshrc  # または source ~/.bashrc
```

---

## 2. age 公開鍵の確認

`.sops.yaml` の設定に使用する公開鍵を確認します。

```bash
grep "public key:" ~/.config/sops/age/keys.txt
```

出力例:

```
# public key: age1ql3z7hjy54pw3hyww5ayyfg7zqgvc7w3j2elw8zmrj2kg5sfn9aqmcac8p
```

`age1...` の部分を以降の手順で `<YOUR_AGE_PUBLIC_KEY>` として使用します。

---

## 3. .sops.yaml の作成

リポジトリルートに `.sops.yaml` を作成し、暗号化ルールを定義します。

```yaml
creation_rules:
  # github ディレクトリの tfvars（.tfvars と .tfvars.enc の両方にマッチ）
  - path_regex: infrastructure/github/terraform\.tfvars(\.enc)?$
    age: "<YOUR_AGE_PUBLIC_KEY>"

  # AWS 環境の tfvars
  - path_regex: infrastructure/aws/environments/prod/terraform\.tfvars(\.enc)?$
    age: "<YOUR_AGE_PUBLIC_KEY>"
```

> **注意**: `<YOUR_AGE_PUBLIC_KEY>` を手順 2 で確認した実際の公開鍵に置き換えてください。

---

## 4. terraform.tfvars の暗号化

平文の `terraform.tfvars` から暗号化された `terraform.tfvars.enc` を生成します。

### 4-1. github/terraform.tfvars の暗号化

```bash
sops -e infrastructure/github/terraform.tfvars > infrastructure/github/terraform.tfvars.enc
```

### 4-2. aws/environments/prod/terraform.tfvars の暗号化

```bash
sops -e infrastructure/aws/environments/prod/terraform.tfvars > infrastructure/aws/environments/prod/terraform.tfvars.enc
```

### 4-3. 暗号化の確認

`.tfvars` は SOPS のネイティブサポート対象外のため、ファイル全体が JSON 形式でバイナリ暗号化されます。

```bash
cat infrastructure/github/terraform.tfvars.enc
```

出力例（ファイル全体が JSON 形式で暗号化）:

```json
{
    "data": "ENC[AES256_GCM,data:xxxxx...,iv:xxxxx,tag:xxxxx,type:str]",
    "sops": {
        "age": [{ "recipient": "age1...", "enc": "..." }],
        "lastmodified": "...",
        "mac": "ENC[...]",
        "version": "3.x.x"
    }
}
```

---

## 5. .gitignore の確認

平文の `terraform.tfvars` が `.gitignore` に含まれていることを確認します（既存の設定を維持）。`terraform.tfvars.enc` は `.gitignore` に含まれていないため、Git 管理対象になります。

```bash
# 各 .gitignore に terraform.tfvars が含まれていることを確認
grep "terraform.tfvars" infrastructure/github/.gitignore
grep "terraform.tfvars" infrastructure/aws/environments/prod/.gitignore
```

> **重要**: `.gitignore` に `terraform.tfvars` と記載されていても、`terraform.tfvars.enc` は別のファイル名なので Git の追跡対象になります。変更は不要です。

---

## 6. Git へのコミット

```bash
git add .sops.yaml
git add infrastructure/github/terraform.tfvars.enc
git add infrastructure/aws/environments/prod/terraform.tfvars.enc
git commit -m "feat(infra): SOPS + age で terraform.tfvars を暗号化しGit管理対象に追加"
```

---

## 7. 日常の運用手順

### 復号して閲覧する

```bash
# ターミナルに復号結果を表示（ディスクには書き込まれない）
sops -d infrastructure/github/terraform.tfvars.enc
```

### 暗号化ファイルを編集する

```bash
# エディタで復号された状態で開き、保存時に自動で再暗号化される
sops infrastructure/github/terraform.tfvars.enc
```

### Terraform の実行

プロセス置換 `<()` を使い、復号された内容をディスクに書き込まずに Terraform へ渡します。

```bash
cd infrastructure/github
terraform plan -var-file=<(sops -d terraform.tfvars.enc)
terraform apply -var-file=<(sops -d terraform.tfvars.enc)
```

```bash
cd infrastructure/aws/environments/prod
terraform plan -var-file=<(sops -d terraform.tfvars.enc)
terraform apply -var-file=<(sops -d terraform.tfvars.enc)
```

> **補足**: `<()` は bash / zsh のプロセス置換機能です。`/dev/fd/XX` というファイルディスクリプタ経由でデータを渡すため、復号された平文がファイルとしてディスク上に残ることはありません。

---

## 8. 新規メンバーのセットアップ

新しいチームメンバーが参加する場合の手順です。

### 8-1. ツールのインストール

```bash
brew install sops age
```

### 8-2. age キーの受け渡し

既存メンバーから安全な手段（対面、パスワードマネージャー等）で age 秘密鍵を受け取り、配置します。

```bash
mkdir -p ~/.config/sops/age
# 受け取った秘密鍵を keys.txt に保存
vim ~/.config/sops/age/keys.txt
chmod 600 ~/.config/sops/age/keys.txt
```

### 8-3. 環境変数の設定

`.bashrc` / `.zshrc` に追加します。

```bash
export SOPS_AGE_KEY_FILE="$HOME/.config/sops/age/keys.txt"
```

### 8-4. 復号の確認

```bash
sops -d infrastructure/github/terraform.tfvars.enc
```

正常に復号できれば完了です。

---

## 9. キーのローテーション

age キーを変更する場合の手順です。

```bash
# 1. 新しいキーペアを生成
age-keygen -o new-key.txt

# 2. .sops.yaml の公開鍵を新しいものに更新

# 3. 全ファイルを新しいキーで再暗号化
sops updatekeys infrastructure/github/terraform.tfvars.enc
sops updatekeys infrastructure/aws/environments/prod/terraform.tfvars.enc

# 4. 新しい秘密鍵を ~/.config/sops/age/keys.txt に配置
# 5. 古い秘密鍵を安全に破棄
```

---

## トラブルシューティング

| 症状 | 原因 | 対処 |
|------|------|------|
| `Failed to get the data key` | 秘密鍵が見つからない | `SOPS_AGE_KEY_FILE` 環境変数を確認、または `~/.config/sops/age/keys.txt` にキーを配置 |
| `no matching creation rules` | `.sops.yaml` のパスが一致しない | `path_regex` とファイルパスの一致を確認（リポジトリルートからの相対パス） |
| `error: process substitution is not supported` | sh で実行している | bash または zsh で実行する。Makefile では `SHELL := /bin/bash` を指定する |

---

## 参考リンク

- [SOPS 公式リポジトリ](https://github.com/getsops/sops)
- [age 公式リポジトリ](https://github.com/FiloSottile/age)
