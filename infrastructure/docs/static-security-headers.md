# 静的配信のセキュリティヘッダー

## 所有と適用範囲

`aws/modules/static_site`の専用ResponseHeadersPolicyを、既存CloudFront distributionのdefaultと`assets/*`の両behaviorへ関連付けます。
HTML・JS・CSS・font等の配信に同じ方針を適用し、API GatewayのCORSや他のアプリ、共有DNSは変更しません。
[CloudFront公式仕様](https://docs.aws.amazon.com/AmazonCloudFront/latest/DeveloperGuide/understanding-response-headers-policies.html)に従い、originの同名headerをoverrideします。
[response headers policy](https://docs.aws.amazon.com/AmazonCloudFront/latest/DeveloperGuide/modifying-response-headers.html)はcache済み応答にも適用されるため、ヘッダー導入のためのS3成果物更新・image配備・cache invalidationは不要です。

## 採用値と理由

| Header | 値・方針 | 理由 |
|---|---|---|
| Strict-Transport-Security | `max-age=86400`、includeSubDomains/preloadなし | HTTPS運用を維持する。初回導入は1日とし、ブラウザの保持期間を限定。他のサブドメインへ広げない |
| X-Content-Type-Options | `nosniff` | JS/CSS等をMIMEで判定させる。実assetのContent-Typeも適用後確認する |
| X-Frame-Options / CSP frame-ancestors | `DENY` / `'none'` | 直接閲覧・URL共有を提供し、他ページへの埋め込みは提供しない |
| Referrer-Policy | `no-referrer` | 外部リンクへ選択URL等を送らない。表示・API利用にRefererは不要 |
| Permissions-Policy | `camera=(), microphone=(), geolocation=()` | 気象表示で使用しない機能を無効化 |
| Content-Security-Policy | 下記 | 外部実行・接続元を制限し、既存のCanvas/Radix表示を維持 |

CSPは`default-src 'none'`を基本に、`script-src 'self'`、`img-src 'self'`、`font-src 'self'`、
`connect-src 'self' https://<既存api_domain_name>`を許可します。base-uri / object-src / frame-ancestors / form-actionはnoneです。
API originはprod rootの既存変数をmoduleへ渡し、wildcardや任意のHTTPS originを許可しません。

styleだけは`style-src 'self' 'unsafe-inline'`にします。Canvasの寸法、tooltip、凡例、Radixのpopup/scroll lockが
動的styleを利用するためです。[style-srcの制限](https://developer.mozilla.org/en-US/docs/Web/HTTP/Reference/Headers/Content-Security-Policy/style-src)と互換性の判断であり、inline scriptやunsafe-evalは許可しません。
style内の注入可能性をすべて排除するものではなく、スクリプトやDOMの安全な取扱いは引き続き必要です。

旧X-XSS-Protectionフィルターの有効化、COOP/COEP、CSPレポート収集基盤は追加しません。
未使用機能の追加やクロスorigin分離を目的にせず、通常の画面表示を保ちます。

## 承認後の適用と確認

本番適用はPRの自己レビュー・CI成功・merge後、最新mainのplanをレビューして別途ユーザー承認を得て行います。

1. 保存planのhash・sourceと対象アカウントを確認してapply。保存planにephemeralなWebhook URLは含まれないため、[通知の適用手順](./api-observability.md)と同じSOPS暗号化入力をapply時にもプロセス内で渡す。distributionがDeployedになるまで待つ。
2. HTTPS GET/HEADでHTML・実JS/CSS/font asset・SPA fallbackを確認し、各header値とContent-Type、実APIの正常通信を確認する。
3. header注入を外した実ブラウザで、東京1872年・指定6都市、画面操作とCSPの検出を確認する。frame拒否とinline script拒否も確認する。
4. apply後のplanが差分0か確認し、証跡を記録して適用の完了を判断する。

## 切り戻し

問題があれば対象header値を修正する通常PR・plan・本番承認で戻します。緊急時もdistributionやbucketを削除せず、
CSPが原因なら専用policy内の当該directiveを戻すかpolicyの関連付けを戻し、反映後の表示を確認します。
[HSTS](https://developer.mozilla.org/en-US/docs/Web/HTTP/Reference/Headers/Strict-Transport-Security)はブラウザが保持します。
policyを外すだけでは既存のHSTS記録は消えないため、必要ならHTTPS応答で`max-age=0`を返して解除し、
未再訪のブラウザは最大1日の期限切れを待つことを考慮します。includeSubDomains/preloadは採用していません。
