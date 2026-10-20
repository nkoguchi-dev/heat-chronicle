# GitHub Actions配備ロールのOIDC境界

配備元は`nkoguchi-dev/heat-chronicle`の`release/prod`です。main統合と本番配備を分けます。

- issuer: `https://token.actions.githubusercontent.com`
- audience: `sts.amazonaws.com`（`StringEquals`）
- subject: `repo:nkoguchi-dev/heat-chronicle:ref:refs/heads/release/prod`（`StringEquals`）
- action: `sts:AssumeRoleWithWebIdentity`

Deploy Backend / Deploy Frontendの手動実行でも`release/prod`を指定します。
main・feature・tag・PR・environmentのsubjectは許可しません。
同じbranch上のworkflowは区別しないため、release/prodの更新権限も管理します。
[GitHubのsubject形式](https://docs.github.com/en/actions/reference/security/oidc)を参照してください。
所有者・repository名・environment・subject形式の変更時はGitHub設定とIAMを同時に照合し、wildcardで回避しません。
mockテストはprincipal/action/audience/subjectと非許可subjectを確認し、実OIDCや配備を代替しません。
本番変更は全体planの生成policyと全差分をレビュー・承認し、実IAM・subject設定・ref契約・差分なしを確認します。
配備を伴わない検証でworkflowを試しに実行しません。
