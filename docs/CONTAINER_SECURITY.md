# 配信用コンテナの検査と更新

対象は`backend/Dockerfile.prod`のLambda用Linux/amd64最終imageです。
PR・main・日次・手動のContainer SecurityはAWS認証なしで候補をbuildし、隔離handler smokeとTrivy検査を行います。
日次の候補buildは、現在稼働中のdigestの再検査ではありません。

## 判定と公開出力

Trivy 0.76.0を公式archiveの固定checksumで導入します。
HIGH/CRITICALは修正版の有無によらず失敗、秘密検出はseverityによらず失敗です。
scanner不調、inventory不足、EOSL、48時間を超えたDB、SBOM生成失敗も失敗にします。
ignore・baseline・呼出元のTRIVY_*による無条件抑制は行いません。
LOW/MEDIUM/UNKNOWNもローカルreportへ残し、到達条件と修正版を確認します。

公開Actionsへ保存するのは件数・検査完了・image ID等のsummary.jsonだけです。
未評価findings・SBOM・raw reportは公開artifactへ保存しません。
詳細は同じ候補をローカル再検査し、所有者専用のGit管理外ディレクトリへ保存します。
秘密検出時はSBOMも生成せず、[失効・調査手順](./SECRET_DETECTION.md)へ進みます。

## buildと更新

base digestを固定し、AL2023のOS packageを更新します。
`--no-cache-filter base`で古い更新RUN cacheを再利用しません。
Poetryはbuilderだけで使い、最終imageからpipとensurepip同梱installerを除きます。
専用dockerignoreで環境ファイル・鍵・不要ファイルをcontextから除きます。
OS repoの変化もあるため、base固定だけで完成imageの同一byteは保証しません。

```sh
docker buildx build --platform linux/amd64 --pull --no-cache-filter base --provenance=false --load -f backend/Dockerfile.prod -t heat-chronicle-local:candidate backend
docker run --rm -i --network none --platform linux/amd64 --entrypoint /var/lang/bin/python -e AWS_EC2_METADATA_DISABLED=true -e AWS_DEFAULT_REGION=ap-northeast-1 -e AWS_ACCESS_KEY_ID=testing -e AWS_SECRET_ACCESS_KEY=testing heat-chronicle-local:candidate - < tools/containers/smoke.py
python3 tools/containers/install.py --bin-dir /private/tmp/heat-container-bin
python3 tools/containers/scan.py --trivy /private/tmp/heat-container-bin/trivy --image heat-chronicle-local:candidate --output-dir /private/tmp/heat-container-report
```

配備は別途承認後に行い、完成manifest digestを保持します。ECRの同一digestのscan完了を確認してLambdaへ反映し、
Active/SuccessfulとResolvedImageUriを照合します。旧imageは切り戻し用に保持します。
実API・通常ブラウザ・新規ログを確認し、cache参照だけで書込成功を主張しません。
稼働digestの検査は配備時・週次・重大advisory発生時に取り直します。
