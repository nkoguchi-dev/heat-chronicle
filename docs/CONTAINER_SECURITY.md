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
固定digestのuvをbuilderだけで使い、uv.lockからruntime依存だけをtask rootへ導入します。
最終imageからuv・開発依存・pip・ensurepip同梱installer・ローカル実行用RIEを除きます。
AWS提供のentrypointとPython Runtime Interface Clientは維持し、Lambdaでは`AWS_LAMBDA_RUNTIME_API`を通じて起動します。
Lambda用imageの単独HTTPエミュレーター起動は提供せず、ローカル開発は既存のhost起動または開発用imageを使います。
`tools/containers/smoke.py`は実handlerに加え、コンテナ内の模擬Runtime APIと小さな専用handlerで、実entrypoint・bootstrapの起動と応答を検査します。
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

## ベース更新とRIE除去の検証（2026-10-25、Issue #260）

Python 3.14 / Linux amd64を維持し、AWSベースdigestを
`252cbb0879717b1c049b9f909d86d06d88e129f3208386d7ba1189d535f5f981`から
`c9cc170aa9743cec54121c00c7192217b021df420eca9e7835ed9442156e4ebe`へ更新した。
旧digestでOS更新後も残ったcurl・libcap・PCRE2・CA証明書の指摘は、新digestの更新済みOS inventoryでは非検出となった。
OS更新処理は維持する。RIE内のGo/chi/x/sysはOS更新では置き換わらず、新ベースにも残っていたため、未使用のRIEを最終imageから除去した。

ローカル最終候補のimage IDは`sha256:81b7ca5d7989f2f086f2e4fd410a46a28b4181fbd0c2fceb06b4375da3babb38`。
Trivy 0.76.0、DB更新時刻`2026-10-25T07:10:41.872962161Z`でOS/Python inventoryを含む検査が完了し、
全severityの指摘0件・秘密0件・SBOM生成成功を確認した。ゲートの8件のテスト、実handlerのhealth・都道府県一覧、
RIEなしのAWS entrypoint/bootstrapから模擬Runtime APIへの応答も成功した。
非該当だったWindows専用APIを含め、RIEの3指摘は部品自体の除去で解消しており、ignore追加や判定基準の緩和はしていない。

この候補の結果を本番解消とは扱わない。本番は選択中digestを別途検査し、公開mainのPython依存更新も含む検査済み候補を配備して、
稼働digestの一致・通常導線・新規ログを確認する。正確な配備対象と実機結果は配備時に記録する。
