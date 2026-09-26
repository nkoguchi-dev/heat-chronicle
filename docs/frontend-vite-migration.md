# フロントエンドVite移行契約

> 確認日: 2026-09-26 / 対象: Issue #135、Next.js 16.3.5、Vite 8.3.1

この文書は、Heat ChronicleのフロントエンドをNext.jsの静的exportからViteの静的SPAへ段階移行するための技術契約を定義する。利用者向けの仕様は変更せず、[`docs/specs/`](./specs/)を正本とする。

## 維持する契約

- 公開画面は`/`の単一画面とし、地点と気温種別は`pref`、`station`、`type`クエリパラメータを正本にする。
- クエリ付きURLへの直接アクセス、再読み込み、共有、戻る・進む操作で同じ状態を復元する。
- UI、API endpoint、Zodによるレスポンス検証、中断・競合制御、月別取得間隔を変更しない。
- production成果物は静的ファイルだけで構成し、実行時Node.jsサーバー、SSR、SSG、Server Components、Server Actionsを導入しない。
- production成果物はS3とCloudFrontで公開し、Browser Smokeでは同じ成果物をproduction用Docker/Nginxから配信する。
- Playwrightの固定API応答と、直接アクセス・再読み込み、キーボード操作、過去データ追加、履歴操作の4つの主要導線を維持する。

単一画面の`/`とクエリパラメータだけでURL状態を表現できるため、Vite移行ではクライアントルーターを導入しない。将来path単位の複数画面が必要になった場合は、そのIssueで直接アクセス、履歴、配信fallbackを含む必要性を再評価する。

## 現行と移行後の実行契約

| 項目           | 現行のNext.js経路                               | Vite移行後の正規経路                                                          |
| -------------- | ----------------------------------------------- | ----------------------------------------------------------------------------- |
| ブラウザー入口 | `src/app/layout.tsx`と`src/app/page.tsx`        | `index.html`と`src/main.tsx`                                                  |
| 画面の接続     | App Routerから`HeatmapPage`を表示               | React rootからProvider、最上位error boundary、`HeatmapPage`を接続             |
| 開発           | `next dev`、`http://localhost:3000`             | `vite`、`http://localhost:3000`、`strictPort: true`                           |
| build          | `next build`                                    | `vite build`                                                                  |
| 成果物         | `frontend/out`                                  | `frontend/dist`                                                               |
| preview        | `npx serve out`                                 | `vite preview`、`http://localhost:4173`、`strictPort: true`                   |
| API URL        | `NEXT_PUBLIC_API_URL`をbuild時に埋め込む        | `VITE_API_URL`をbuild時に埋め込む                                             |
| ローカルAPI    | ブラウザーから`http://localhost:8000`へ直接接続 | ブラウザーは同一originの`/api`を使用し、Vite dev/preview proxyがFastAPIへ転送 |
| production API | GitHub Actions variableの絶対URL                | GitHub Actions variable `VITE_API_URL`の絶対URL                               |
| 静的asset      | `/_next/static/*`                               | `/assets/*`のcontent hash付きasset                                            |

`VITE_API_URL`はブラウザーへ公開される非機密値である。本番buildではAPIのHTTP(S) originを必須とし、API pathは既存どおり`/api/...`を連結する。ローカルのdev/previewでは未設定を許可して同一originを使う。

Vite serverだけが読む`HEAT_CHRONICLE_API_PROXY_TARGET`でproxy先を上書きできるようにし、未設定時は`http://127.0.0.1:8000`とする。この値はクライアントbundleへ公開しない。HTTP(S) origin以外、資格情報、path、query、fragmentを含む値は起動時に拒否する。`/api` prefixは書き換えずFastAPIへ転送する。

## Next.js固有責務の置換

追跡対象ファイルと参照箇所を検索した結果、現在のNext.js固有利用はApp Routerのlayout/page/errorとicon、`'use client'` directive、`next/font`、metadata、`next.config.ts`の静的export、Next.js type generationとTypeScript plugin、ESLint preset、`process.env.NEXT_PUBLIC_API_URL`、`/_next/static/`のcache設定である。SSR、Server Components、Server Actions、Next.js API Routes、動的routeは利用していない。移行後は次のように置き換える。

- title、description、lang、iconは`index.html`が所有する。
- GeistとGeist Monoはbuildへ含め、既存のCSS変数と表示を維持する。実行時に外部fontを取得しない。
- Providerと`SystemClock`の生成はフレームワーク非依存のapp shellが所有する。
- 想定外エラーの表示、ログ、再試行は最上位のReact error boundaryが所有する。
- TypeScript、ESLint、coverageはViteの入口と設定を対象にし、Next.js生成物への依存と除外を撤去する。

## 配信契約

- `frontend/Dockerfile.prod`は`frontend/dist`をNginxへコピーする。Nginxは`/assets/`を1年間immutable cacheとし、HTMLは長期cacheしない。
- Nginxの未知pathから`index.html`へのfallbackは維持する。現時点の公開pathは`/`だけだが、直接アクセス時にも同じSPA入口を返すためである。
- `scripts/deploy-frontend.sh`は既存S3 bucketへ`frontend/dist/assets`を先に同期して旧ハッシュ付きassetを残し、次に`frontend/dist`のrootを`assets/`除外・`--delete`付きで同期する。成功後に既存CloudFront distributionの`/*`をinvalidateする。
- CloudFrontのS3 origin、OAC、証明書、DNS、`/index.html`への403/404 fallbackは維持する。長期cache対象だけを`/_next/static/*`から`/assets/*`へ変更し、1年間のimmutable cacheとする。HTMLとその他の公開ファイルは既存のdefault behaviorに残し、default TTL 5分とデプロイ時invalidationによって長期cacheさせない。
- 切替前のrollback単位は直前の正常な`release/prod` commitとする。同じworkflowでそのcommitをbuild・同期し、CloudFrontをinvalidateする。S3内の旧Next.js assetは`--delete`で消えるため、S3上の残存物をrollback元にしない。

### release/prodへの適用と復旧（#170で実施）

#143〜#145では本番へのpush、Terraform apply、S3同期を実行していない。#170で人による本番操作の確認を得てから、以下を実施する。

1. 現在正常に配信中の`release/prod` commit、公開URL、GitHub Actionsの`Deploy Frontend`実行結果を記録する。旧workflowのrollback経路を維持するため、まず#143のマージcommitのGitHub Terraform定義で`VITE_API_URL`の追加だけをplan・applyし、`NEXT_PUBLIC_API_URL`を残す。AWS TerraformはCloudFront cache pathの変更と付随するbucket policyの再評価をplanで確認してからapplyする。いずれも人の本番操作確認を得る。
2. `release/prod`を更新する前に、`VITE_API_URL`を使う`npm run build`で`frontend/dist/index.html`と`frontend/dist/assets/`を生成し、`bash scripts/deploy-frontend.sh`の同期対象が既存のフロントエンド専用S3 bucketであることを確認する。
3. 承認済みcommitを`release/prod`へ取り込み、`Deploy Frontend`のbuild、2段階のS3同期、CloudFrontの`/*` invalidation成功を確認する。公開URLの`/`とクエリ付きURL、`/assets/`配下のファイル、実APIへの接続は#170の本番手動確認で確認する。
4. 本番が正常でrollback判断が済んでから、最新mainのGitHub Terraformをplan・applyして旧`NEXT_PUBLIC_API_URL` variableを削除する。先に最新定義をapplyすると旧workflowのrollbackが動かなくなるため順序を入れ替えない。
5. 失敗時は追加の本番操作について人に確認した上で、記録した正常commitの内容へ`release/prod`上でrevertする新しいcommitを作成してpushする。旧variableの削除後なら、先に#143のGitHub Terraform定義で旧variableを復旧してからrevertする。S3に残るファイルやforce pushを復旧元にしない。

`--delete`は専用bucketのrootにだけ作用し、`assets/`は除外する。新HTMLの参照先を先に配置し、旧Vite assetを残すことで開いたタブからの参照切れを避ける。古いVite assetの整理は利用状況を確認して別途行う。デプロイスクリプトは`index.html`とassetファイルの欠落時に同期を止める。rootのHTML等には5分、ハッシュ付きassetには1年のimmutable cache-controlを指定する。CloudFrontのdefault behaviorは5分、`assets/*` behaviorは1年であり、S3 origin・OAC・証明書・DNS・403/404 fallbackは変更しない。

## Sub-Issueの責務と中間状態

| Issue | 責務                                                                        | マージ時に維持する中間状態                                        |
| ----- | --------------------------------------------------------------------------- | ----------------------------------------------------------------- |
| #140  | ViteのHTML/React入口、Provider、metadata、font、error boundary、buildを追加 | Vite経路と既存Next.js経路の両方をbuildできる                      |
| #141  | `VITE_API_URL`、dev/preview proxy、API clientとテストを移行                 | Vite経路でローカル・本番API接続契約が成立し、Next.js配信は残る    |
| #142  | production Docker/NginxとBrowser Smokeを`dist`へ切替                        | Vite成果物の決定的な主要導線をNginx上で確認できる                 |
| #143  | Actions、deploy script、CloudFront asset cacheをViteへ切替                  | 既存S3・CloudFrontへ`dist`を配信でき、Next.js依存はまだ撤去しない |
| #144  | Next.js依存、App Router、旧設定、開発用frontend Docker/Composeを撤去        | Viteだけが正規の開発・build・配信経路になる                       |
| #145  | Vite移行の事前品質検査とBrowser Smokeを確認                                 | 本番適用・最終確認は#170へ引き継ぐ                                |
| #170  | 最新mainの再検査、release/prod、本番手動確認、移行文書の整理                | 対象commitと環境に結び付けて親Issue #135の完了条件を確認する      |

実装は#140から#144まで順にmainへマージ済みである。事前検証#145の後に、本番適用と最終確認#170を行う。利用者向け仕様を変えないため、この移行契約だけではMarkdown仕様書、Gherkin、Unit、Component、Browser Smokeの期待値を変更しない。

## 完了確認

最終状態では`npm ci`後にformat、lint、typecheck、test:coverage、build、Browser Smokeを実行する。#170ではさらにmainとrelease/prodのrequired checks、既存公開URL、本番APIとの疎通、ルート`AGENTS.md`に定義された手動スモークを確認する。本番適用は人の確認を得てから行う。
