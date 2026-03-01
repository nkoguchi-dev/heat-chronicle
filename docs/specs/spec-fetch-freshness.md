# 仕様書: データ鮮度管理（Fetch Freshness）

## 1. 背景と課題

### 現状の仕組み

気象庁サイトからのデータ取得は月単位で行われ、取得済みの月は `fetch-log` テーブルに記録される。`fetch-log` にエントリが存在する月は再取得をスキップし、DB のキャッシュデータを返す。

### 問題点

このキャッシュは永久に有効であるため、以下のケースで不完全なデータが固定化される。

1. **当月途中の取得**: 2月15日に取得すると、2月16日〜28日のデータが欠落したまま固定される
2. **長期間未アクセス後の再訪問**: 2月15日に取得後、8月15日に再アクセスしても2月のデータは2月15日時点のまま
3. **月末境界のデータ未確定**: 3月1日時点では2月28日（or 29日）のデータが気象庁側で未公開の可能性がある

## 2. 解決方針

「月のデータが確定済みかどうか」をドメインモデルとして表現し、確定/未確定に応じてキャッシュ戦略を切り替える。

## 3. ドメインモデル設計

### 3.1 値オブジェクト: `FetchStatus`

月ごとのデータ取得状態を表現する値オブジェクト。

```
場所: backend/app/domain/fetch_freshness.py
```

```python
from enum import Enum

class FetchStatus(Enum):
    """月データの取得状態"""
    UNFETCHED = "unfetched"             # 未取得（fetch-logにエントリなし）
    NEEDS_REFRESH = "needs_refresh"     # 再取得が必要（未確定かつTTL期限切れ）
    TEMPORARILY_CACHED = "temporarily_cached"  # 一時キャッシュ中（未確定だがTTL期限内）
    FINALIZED = "finalized"             # 確定済み（再取得不要）
```

### 3.2 ドメインサービス: `FetchFreshnessPolicy`

取得状態の判定ロジックをカプセル化するドメインサービス。

```
場所: backend/app/domain/fetch_freshness.py
```

#### 定数

| 名称 | 値 | 説明 |
|------|-----|------|
| `GRACE_PERIOD_DAYS` | 2 | 月末からデータ確定までの猶予日数 |
| `TEMPORARY_CACHE_TTL_HOURS` | 24 | 未確定月の一時キャッシュ有効時間 |

#### 判定ロジック

```python
class FetchFreshnessPolicy:
    GRACE_PERIOD_DAYS: int = 2
    TEMPORARY_CACHE_TTL_HOURS: int = 24

    def evaluate(
        self,
        year: int,
        month: int,
        fetched_at: datetime | None,  # fetch-logのfetched_at（エントリなしならNone）
        now: datetime,                # 現在日時（UTC）
    ) -> FetchStatus:
        """月データの取得状態を判定する"""
```

#### 判定フロー

```
入力: year, month, fetched_at, now
  │
  ├─ fetched_at が None
  │   └─ → UNFETCHED
  │
  ├─ fetched_at > 対象月の末日 + GRACE_PERIOD_DAYS（2日）
  │   └─ → FINALIZED
  │
  ├─ now - fetched_at < TEMPORARY_CACHE_TTL_HOURS（24時間）
  │   └─ → TEMPORARILY_CACHED
  │
  └─ それ以外
      └─ → NEEDS_REFRESH
```

#### 判定の意味

| FetchStatus | 意味 | アクション |
|-------------|------|-----------|
| `UNFETCHED` | 一度も取得していない | JMA からスクレイピングし、fetch-log に記録 |
| `NEEDS_REFRESH` | 取得済みだがデータ未確定かつ TTL 切れ | JMA から再スクレイピングし、fetch-log の `fetched_at` を更新 |
| `TEMPORARILY_CACHED` | 取得済みで未確定だが TTL 内 | DB のキャッシュデータを返す（スクレイピングしない） |
| `FINALIZED` | 月末＋猶予期間を過ぎた後に取得済み | DB のキャッシュデータを返す（以降再取得しない） |

### 3.3 「確定済み」の定義

月のデータが**確定済み**とみなされる条件:

```
fetched_at > その月の末日 + 2日（GRACE_PERIOD_DAYS）
```

この条件は「月が終わり、かつ気象庁がデータを確定公開するのに十分な時間が経過した後に取得されたデータである」ことを保証する。

#### 根拠

- 気象庁は翌日の早朝（2:00頃）にはデータを更新すると推定される
- 月末日の翌日（1日）の早朝に最終日のデータが公開される
- 猶予2日は安全マージンとして十分

### 3.4 具体例による検証

#### 例1: 当月途中の取得

```
状況: 2026年2月15日 10:00 に2月データを取得
対象月末日: 2/28  →  確定ライン: 3/2

evaluate(2026, 2, fetched_at=2/15 10:00, now=2/15 10:00)
  fetched_at(2/15) > 3/2 ? → No
  now - fetched_at < 24h ? → Yes（0時間差）
  → TEMPORARILY_CACHED ✅ 取得直後なのでキャッシュ利用

evaluate(2026, 2, fetched_at=2/15 10:00, now=2/16 12:00)
  fetched_at(2/15) > 3/2 ? → No
  now - fetched_at < 24h ? → No（26時間経過）
  → NEEDS_REFRESH ✅ TTL切れなので再取得
```

#### 例2: 長期間未アクセス後の再訪問

```
状況: 2月15日に取得後、8月15日に再アクセス
対象月末日: 2/28  →  確定ライン: 3/2

evaluate(2026, 2, fetched_at=2/15, now=8/15)
  fetched_at(2/15) > 3/2 ? → No
  now - fetched_at < 24h ? → No（約180日経過）
  → NEEDS_REFRESH ✅ 再取得される

再取得後:
evaluate(2026, 2, fetched_at=8/15, now=8/15)
  fetched_at(8/15) > 3/2 ? → Yes
  → FINALIZED ✅ 以降は永久キャッシュ
```

#### 例3: 月境界のデータ未確定

```
状況: 3月1日に2月データを取得
対象月末日: 2/28  →  確定ライン: 3/2

evaluate(2026, 2, fetched_at=3/1, now=3/1)
  fetched_at(3/1) > 3/2 ? → No
  now - fetched_at < 24h ? → Yes
  → TEMPORARILY_CACHED ✅ まだ未確定なのでキャッシュ

evaluate(2026, 2, fetched_at=3/1, now=3/2 12:00)
  fetched_at(3/1) > 3/2 ? → No
  now - fetched_at < 24h ? → No
  → NEEDS_REFRESH ✅ 再取得される

再取得後:
evaluate(2026, 2, fetched_at=3/2 12:00, now=3/2 12:00)
  fetched_at(3/2 12:00) > 3/2 00:00 ? → Yes
  → FINALIZED ✅ 確定
```

#### 例4: 当月のデータ（常に未確定）

```
状況: 3月中に3月のデータを取得
対象月末日: 3/31  →  確定ライン: 4/2

evaluate(2026, 3, fetched_at=3/10, now=3/10)
  fetched_at(3/10) > 4/2 ? → No
  now - fetched_at < 24h ? → Yes
  → TEMPORARILY_CACHED ✅ 当日はキャッシュ

evaluate(2026, 3, fetched_at=3/10, now=3/11 12:00)
  fetched_at(3/10) > 4/2 ? → No
  now - fetched_at < 24h ? → No
  → NEEDS_REFRESH ✅ 翌日には再取得
```

#### 例5: 過去の確定データ（2024年のデータを2026年に取得）

```
evaluate(2024, 6, fetched_at=2026/3/1, now=2026/3/1)
  fetched_at(2026/3/1) > 2024/7/2 ? → Yes
  → FINALIZED ✅ 初回取得で即確定
```

## 4. 実装方針

### 4.1 変更対象ファイル

| ファイル | 変更内容 |
|---------|---------|
| `domain/fetch_freshness.py` | **新規作成** — `FetchStatus` 列挙型 + `FetchFreshnessPolicy` ドメインサービス |
| `infrastructure/repositories/temperature_repository.py` | `get_fetched_months()` の返り値を `dict[tuple[int, int], datetime]` に変更（`fetched_at` を含める） |
| `application/scrape_service.py` | `FetchFreshnessPolicy` を利用した判定ロジックに置き換え |
| `application/temperature_service.py` | `fetched_months` メタデータ生成ロジックの調整（必要に応じて） |

### 4.2 fetch-log テーブルへの影響

- スキーマ変更は不要（`fetched_at` は既に記録されている）
- 再取得時は `put_item` による上書きで `fetched_at` が自然に更新される（DynamoDB の `put_item` は同一キーで上書き）
- 既存データとの互換性に問題なし

### 4.3 レイヤー間の依存関係

```
Presentation (temperature.py)
    ↓
Application (scrape_service.py)
    ↓ uses
Domain (fetch_freshness.py)  ← 純粋なドメインロジック（外部依存なし）
    ↑ reads from
Infrastructure (temperature_repository.py)
```

`FetchFreshnessPolicy` はドメイン層に配置し、外部依存を持たない純粋な判定ロジックとする。`datetime` のみを入力として受け取り、テスト容易性を確保する。

### 4.4 scrape_service.py の変更イメージ

```python
# Before（現在のコード）
fetched_months = self.temp_repo.get_fetched_months(station_id)
fetched_set = set(fetched_months)
if (year, month) not in fetched_set:
    # スクレイピング実行
    ...

# After（変更後）
fetched_months = self.temp_repo.get_fetched_months(station_id)  # dict[tuple, datetime]
fetched_at = fetched_months.get((year, month))  # datetime | None

policy = FetchFreshnessPolicy()
status = policy.evaluate(year, month, fetched_at, datetime.now(timezone.utc))

if status in (FetchStatus.UNFETCHED, FetchStatus.NEEDS_REFRESH):
    # スクレイピング実行 + fetch-log 更新
    ...
# TEMPORARILY_CACHED, FINALIZED の場合はDBキャッシュを返す
```

### 4.5 テスト方針

`FetchFreshnessPolicy` は純粋関数的なドメインロジックであるため、`now` を注入することで容易にテスト可能。

```
テストファイル: backend/tests/domain/test_fetch_freshness.py
```

テストケース:

1. **UNFETCHED**: `fetched_at=None` → `UNFETCHED`
2. **FINALIZED（過去月を月末＋猶予後に取得）**: 確定ラインを超えた `fetched_at` → `FINALIZED`
3. **TEMPORARILY_CACHED（取得から24時間以内）**: TTL内 → `TEMPORARILY_CACHED`
4. **NEEDS_REFRESH（未確定かつTTL切れ）**: 確定ライン前の `fetched_at` でTTL超過 → `NEEDS_REFRESH`
5. **月末境界**: 月末日翌日〜猶予期間内の取得 → 正しく未確定と判定
6. **うるう年**: 2月29日を含む月の末日計算が正しいこと
7. **過去データの即確定**: 数年前の月を初回取得 → `FINALIZED`
8. **年跨ぎ**: 12月のデータの確定ラインが翌年1月2日であること

## 5. 設計判断の記録

### なぜ TTL だけでなく「確定判定」を組み合わせるのか

TTL のみ（例: 24時間で再取得）だと、何年も前の確定データまで24時間ごとに再取得してしまう。「月末＋猶予を過ぎた後に取得されたか」という確定判定を先に行うことで、確定データへの不要なリクエストを完全に排除できる。

### なぜ猶予日数を2日にしたのか

- 気象庁は翌日の早朝（推定2:00頃）にデータを更新する
- 月末日のデータは翌月1日の早朝に公開される
- 1日でも理論上は十分だが、公開遅延やメンテナンスを考慮して2日とした

### なぜ一時キャッシュTTLを24時間にしたのか

- 気象庁への過度なリクエストを避ける（礼儀としてのレートリミット）
- 日次データであるため、1日1回の更新で実用上十分
- ユーザーが同日中に複数回アクセスしても毎回スクレイピングが走ることを防止
