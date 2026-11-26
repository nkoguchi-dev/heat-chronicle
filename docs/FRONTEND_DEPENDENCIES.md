# frontend開発依存の検査と生成CSS

## 対象と判断

2026-10-20の全依存npm auditはhigh 7・moderate 1、omit=devは0でした。
8件は独立した8つの脆弱性ではなく、braces / fast-uriの一次指摘が親依存へ伝播したものです。

| 一次指摘 | 参照時の条件 | このリポジトリの経路と対応 |
|---|---|---|
| [braces GHSA-vfj7-8cjw-p6xm](https://github.com/advisories/GHSA-vfj7-8cjw-p6xm) | 3.0.3までの深いbrace patternによるstack exhaustion、修正版なし | shadcnのfast-glob/micromatch、registry・ts-morph系列。通常build/testで不要な生成CLIと依存を除去 |
| [fast-uri GHSA-hrr3-gc8f-f4qj](https://github.com/advisories/GHSA-hrr3-gc8f-f4qj) | 3.0.0〜3.1.7のhost正規化、3.1.8で修正 | shadcn → MCP SDK/ajv/ajv-formats系列。CLI除去とともに不要な依存を除去 |

これらはCLIが扱うpattern/registry/schema等の入力が関心事で、公開気象APIや配信JSから同じ経路が呼ばれるとは扱いません。
開発環境のリスクも残さず除去し、強制major更新や無条件のaudit抑制は行いません。
shadcn経由のために置いていた@hono/node-server overrideは、対象依存が消えたこととaudit成功を確認し、理由メタデータも同じ変更で除去しました。

## 生成済みUIと必要なCSS

[shadcn/uiの方式](https://ui.shadcn.com/docs)に合わせ、生成済みUIは所有するソースとして維持します。
このリポジトリのapp/CI/build/testはshadcn CLIを実行しません。一方、globals.cssにはshadcn/tailwind.cssの参照があったため、
単にpackageを削除するだけではbuildできません。最初のCLI/import調査ではCSS参照を見落とし、fresh buildで検出して修正しました。

以前のlockfileとSHA512が一致するshadcn 4.21.5 archiveから、dist/tailwind.cssだけを
[vendored stylesheet](../frontend/vendor/shadcn/tailwind.css)へ保存しました。元payloadは改変せず、MIT告知を先頭へ付加しています。
[Prettier除外](../frontend/.prettierignore)はこの検証済みの1ファイルだけで、upstreamの形式を保持するためです。
Tailwind compileがCSSコメントを除くため、[元MITライセンス](../frontend/public/shadcn-tailwind-LICENSE.txt)を配信成果物にもコピーします。
CLI/registry/MCP側のJavaScriptはコピーしません。components.jsonと生成済みUIは維持します。

将来コンポーネント生成が必要なときは、CLI version・取得元・registry入力をその作業で確認し、生成差分をレビューします。
CSS更新も元archiveのversion/integrity・payload・ライセンスと生成成果物を確認して通常PRにします。
常時installする依存へ生成CLIを戻す場合は、新しいaudit結果と実行目的を確認します。

## 継続検査

依存更新時はローカルで`npm audit --json`と`npm audit --omit=dev --json`を実行し、開発依存を含む全依存と本番依存を比較します。
Moderateを含む各指摘・依存経路・修正版を確認し、照会失敗や除外もPRへ記録します。
`--audit-level=high`の終了コードだけではModerate以下の非検出を確認できないため、安全の根拠にしません。
例外やoverrideには理由・期限・解除条件を通常PRで記録します。
公開側の既存依存更新を維持した上で未使用CLIを取り除きます。移植元のbuild同一性や過去の件数は、この統合後の成果物の検証結果として扱いません。

## minimatchの限定override

[GHSA-g3hv-75wg-m249](https://github.com/advisories/GHSA-g3hv-75wg-m249)の修正版は11.0.1以降です。
ESLint、@eslint/config-array、typescript-eslintは修正版を通常解決するため、これらのoverrideは除去します。
`eslint-plugin-jsx-a11y-x@0.2.0`だけは10系を要求するため、この親に限定して最新安定版11.0.9をoverrideします（Issue #294）。
この開発用lint経路が使うMinimatchとminimatchのAPI互換性は実際のlint・型検査・テスト・buildで確認します。
アプリから直接利用せず、本番はdistだけを静的配信します。
親が修正版を通常解決できるようになったらoverrideを除去し、fresh install・`npm ls`・全依存と`--omit=dev`のaudit・品質検査を再実行します。

## TypeScriptのcompilerとlint

`tsc`と型付きESLintはTypeScript 6.0.3へ統一します。typescript-eslint 8.74.0のpeer範囲は`>=4.8.4 <6.1.0`です。
TypeScript 7.0.2の別名依存はこの範囲外で、typescript-eslintの任意peerが要求する7.1系にも適合しないため除去します。
7系への更新はlint側の対応後に行い、peer制約を無視するインストールは行いません。
