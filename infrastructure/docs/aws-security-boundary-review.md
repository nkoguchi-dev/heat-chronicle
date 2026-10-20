# AWSの公開境界と実行権限の点検

コード定義と実環境は別々に確認します。実識別子、state、raw plan、秘密値、運用監査証跡は公開しません。

- S3: Block Public Access、CloudFront OAC、bucket policyのdistribution条件。
- CloudFront: HTTPS、TLS、origin、[header policy](./static-security-headers.md)。
- API Gateway: domain、route、[容量](./api-capacity.md)、[CORS](./api-cors.md)、access log。
- Lambda: [実行権限](./lambda-execution-permissions.md)、resource policy、イベント源、稼働digest。
- ECR: [取得policy](./ecr-image-retrieval.md)、保持image、実scan状態。
- GitHub: [OIDC](./github-oidc-deployment.md)、release ref、required checks。
- state: backend所有元・暗号化・versioning・権限。複数rootで同じ資源を管理しない。

監査は読み取りから始め、未確認を未実装・不存在と断定しません。修正は独立したIssue・PR・planに分けます。
frontend復旧はbucketの過去versionだけに依存せず、既知commitから再buildします。
停止・復旧の検証は別途行い、このチェックリストや統合だけで実施済みとは扱いません。
