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

Frontend quality checksで`npm audit --audit-level=high`を実行し、開発依存も含めhigh/criticalを失敗にします。
moderate以下も確認し、例外やoverrideには理由・期限・解除条件を通常PRで記録します。
公開側の既存依存更新を維持した上で未使用CLIを取り除きます。移植元のbuild同一性や過去の件数は、この統合後の成果物の検証結果として扱いません。

## minimatchの限定override（2026-11-01）

[GHSA-g3hv-75wg-m249](https://github.com/advisories/GHSA-g3hv-75wg-m249)は、
未信頼のglobを`optimizationLevel >= 2`で前処理する場合のCPU・メモリ消費を扱います。
対象は11.0.1未満で、10.2.6も修正版ではありません。
調査時の10.2.5は次の4経路（すべてdev依存）に集約されていました。

- eslint 10.13.0 → minimatch
- eslint 10.13.0 → @eslint/config-array 0.23.5 → minimatch
- typescript-eslint 8.72.0 → @typescript-eslint/typescript-estree 8.72.0 → minimatch
- eslint-plugin-jsx-a11y-x 0.2.0 → minimatch

各親の最新版も10系を要求しており、親更新だけでは解消しないため、上記の親に限定して
minimatch 11.0.1へoverrideします。推移依存の親は調査した版に限定します。
直接依存の親はnpmのoverride制約に合わせパッケージ名で指定するため、親更新時にも再評価します。
無条件の全体overrideや`audit fix --force`は使用しません。
2026-12-01までに再評価し、全親が修正版を通常解決できるようになったら、overrideを除去して
fresh install・全依存経路・audit・品質検査を再確認します。

11系は内部matcherを変更し、`makeRe`・`AST`等のAPIを削除しています。
実際の4経路は`Minimatch`の生成・`match`（partialを含む）・`pattern`と名前付き`minimatch`を使用し、
削除されたAPIは使用していません。Node要件は両版とも`18 || 20 || >=22`です。
更新前後のESLint診断と対象ファイル集合を比較し、実際のlint・型検査・テスト・buildでも互換性を確認します。

ESLintのCLI・設定glob、typescript-estreeのallowDefaultProject、アクセシビリティルールの
設定パターンが入力元です。呼び出し元に`optimizationLevel >= 2`指定はなく、既定値は1です。
現行設定にも該当指定や未信頼globの受付はなく、アプリソースからの直接利用もありません。
`npm run build`はViteのみを実行し、これらのlint処理を呼びません。
本番frontendは`dist/`だけを静的配信し、Dockerの最終段にもnode_modulesをコピーしません。
そのため、調査したコードと配信構成では公開入力から該当処理への経路は確認されませんでした。
これは稼働中の本番成果物を照合した結果ではなく、本番配備・実環境照合は対象外です。
