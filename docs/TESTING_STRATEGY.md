# テスト戦略

利用者から見える仕様はMarkdown仕様書、具体的な受け入れ条件はGherkinを正本とする。同じ振る舞いをすべてBrowser Smokeへ重複させず、退行を安定して検出でき、失敗原因を特定しやすいテスト層で確認する。

## テスト層の責務

| テスト層      | 責務                                                                             |
| ------------- | -------------------------------------------------------------------------------- |
| Unit          | URL変換、日付・気温変換、入力境界、データ結合、キャッシュ鮮度などの純粋ロジック  |
| Integration   | フロントエンドのHTTP境界、FastAPI、DynamoDB Local、外部データ境界の変換とエラー  |
| Component     | 利用者に見える表示、操作、ローディング、進捗、エラー、再試行                     |
| Browser Smoke | production静的配信、直接アクセス、再読み込み、履歴、キーボード操作、主要画面統合 |
| 本番手動確認  | 実AWS、実API、実データとの疎通、視覚品質、レスポンシブ表示                       |

GherkinはBrowser Smokeの実装形式ではない。Gherkinを追加または変更したPull Requestでは関連テストを検索し、最適な層での追加・更新、または更新不要とした判断を自己レビューへ記録する。Gherkinと個別テスト名の対応表は管理しない。

## Browser Smokeの境界

Browser Smokeでは、production用の静的成果物を実ブラウザで配信し、外部サービスに依存しない固定応答を使って次の主要導線を確認する。

1. 地点と気温種別を含むURLへの直接アクセスと再読み込み
2. キーボードによる都道府県と観測地点の選択
3. 最高・最低・平均気温の切替
4. 過去50年分の追加と既存データの維持
5. 戻る・進む操作による地点と気温種別の復元

PlaywrightとChromiumを使い、`frontend/Dockerfile.prod`で構築したproduction静的成果物をNginxから配信して確認する。
API通信はブラウザコンテキストで固定応答へ置き換え、未定義リクエストはテスト失敗とする。

境界値、APIエラー分類、再試行、リクエスト中断、古いレスポンスの無視、月別取得間隔は、Unit、Integration、Componentテストを優先する。

## 実行タイミング

- Pull Request前に、変更領域のformat、lint、型チェック、Unit・Integration・Componentテスト、coverage、production buildを実行する
- Pull Requestとmainへのpushで同じ決定的なBrowser Smokeを実行する
- デプロイ後は、実AWS、実API、実データとの疎通を本番サイトで手動確認する
- 仕様、画面、スタイル、配信構成を変更した場合は、必要に応じて視覚品質、レスポンシブ表示、キーボード操作を探索的に確認する
- 失敗、警告、未実施項目は理由と影響をPull Requestへ記録する

Browser Smokeはリポジトリルートで`sh tools/run-browser-smoke.sh`を実行する。使用中のポートを避ける場合は
`E2E_PORT`を指定する。失敗時は`frontend/test-results/`のtrace・screenshotと
`frontend/playwright-report/`のHTML reportを確認する。GitHub Actionsでは同じ成果物を失敗時artifactとして保存する。

## 本番手動確認

本番手動確認は決定的なBrowser Smokeとは別の層として維持する。実施する地点と操作はルート[`AGENTS.md`](../AGENTS.md)の「本番環境の動作確認」を正本とし、実AWS、実API、気象庁データを利用した結果を確認する。
