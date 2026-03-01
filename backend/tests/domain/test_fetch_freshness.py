from datetime import datetime, timedelta, timezone

import pytest

from app.domain.fetch_freshness import FetchFreshnessPolicy, FetchStatus

UTC = timezone.utc


def make_dt(year: int, month: int, day: int, hour: int = 0) -> datetime:
    return datetime(year, month, day, hour, tzinfo=UTC)


@pytest.fixture
def policy() -> FetchFreshnessPolicy:
    return FetchFreshnessPolicy()


class TestFetchFreshnessPolicy:
    def test_unfetched_when_fetched_at_is_none(
        self, policy: FetchFreshnessPolicy
    ) -> None:
        """fetched_at=None のとき UNFETCHED を返す"""
        now = make_dt(2026, 3, 1)
        status = policy.evaluate(2026, 2, None, now)
        assert status == FetchStatus.UNFETCHED

    def test_finalized_when_fetched_after_finalize_line(
        self, policy: FetchFreshnessPolicy
    ) -> None:
        """確定ライン（月末 + 猶予期間2日）を超えた fetched_at なら FINALIZED"""
        # 1月のデータ: 確定ライン = 1/31 + 2日 = 2/2
        # fetched_at = 2/3 (確定ライン超え)
        fetched_at = make_dt(2026, 2, 3)
        now = make_dt(2026, 3, 1)
        status = policy.evaluate(2026, 1, fetched_at, now)
        assert status == FetchStatus.FINALIZED

    def test_temporarily_cached_within_ttl(self, policy: FetchFreshnessPolicy) -> None:
        """TTL 内（24時間以内）なら TEMPORARILY_CACHED"""
        now = make_dt(2026, 2, 15, 12)
        fetched_at = now - timedelta(hours=23)
        status = policy.evaluate(2026, 2, fetched_at, now)
        assert status == FetchStatus.TEMPORARILY_CACHED

    def test_needs_refresh_when_unfinalzed_and_ttl_expired(
        self, policy: FetchFreshnessPolicy
    ) -> None:
        """未確定かつ TTL 超過なら NEEDS_REFRESH"""
        now = make_dt(2026, 2, 15, 12)
        fetched_at = now - timedelta(hours=25)
        status = policy.evaluate(2026, 2, fetched_at, now)
        assert status == FetchStatus.NEEDS_REFRESH

    def test_month_end_boundary_temporarily_cached_then_needs_refresh(
        self, policy: FetchFreshnessPolicy
    ) -> None:
        """月末境界: 翌月1日〜猶予期間内の取得 → TTL 内は TEMPORARILY_CACHED、超過後は NEEDS_REFRESH"""
        # 2月末: 確定ライン = 2/28 + 2日 = 3/2
        # fetched_at = 3/1（確定ライン以前）
        fetched_at = make_dt(2026, 3, 1, 0)

        # TTL 内（取得直後）
        now_within_ttl = fetched_at + timedelta(hours=12)
        status = policy.evaluate(2026, 2, fetched_at, now_within_ttl)
        assert status == FetchStatus.TEMPORARILY_CACHED

        # TTL 超過後
        now_expired = fetched_at + timedelta(hours=25)
        status = policy.evaluate(2026, 2, fetched_at, now_expired)
        assert status == FetchStatus.NEEDS_REFRESH

    def test_leap_year_february(self, policy: FetchFreshnessPolicy) -> None:
        """うるう年: 2月29日を含む月の末日計算が正しいこと"""
        # 2024年2月: うるう年なので末日は29日
        # 確定ライン = 2/29 + 2日 = 3/2
        fetched_at = make_dt(2024, 3, 3)  # 確定ライン超え
        now = make_dt(2024, 4, 1)
        status = policy.evaluate(2024, 2, fetched_at, now)
        assert status == FetchStatus.FINALIZED

        # 確定ライン未満（3/2 当日はまだ未確定）
        fetched_at_before = make_dt(2024, 2, 29)
        now_after_ttl = fetched_at_before + timedelta(hours=25)
        status = policy.evaluate(2024, 2, fetched_at_before, now_after_ttl)
        assert status == FetchStatus.NEEDS_REFRESH

    def test_past_data_finalized_on_first_fetch(
        self, policy: FetchFreshnessPolicy
    ) -> None:
        """過去データの即確定: 数年前の月を初回取得 → FINALIZED"""
        # 2020年6月のデータを2026年3月に取得
        fetched_at = make_dt(2026, 3, 1)
        now = make_dt(2026, 3, 1, 1)
        status = policy.evaluate(2020, 6, fetched_at, now)
        assert status == FetchStatus.FINALIZED

    def test_year_boundary_december_finalizes_in_january(
        self, policy: FetchFreshnessPolicy
    ) -> None:
        """年跨ぎ: 12月データの確定ラインが翌年1月2日"""
        # 12月の末日 = 12/31, 確定ライン = 12/31 + 2日 = 翌年1/2
        # fetched_at = 1/3（確定ライン超え）
        fetched_at = make_dt(2026, 1, 3)
        now = make_dt(2026, 3, 1)
        status = policy.evaluate(2025, 12, fetched_at, now)
        assert status == FetchStatus.FINALIZED

        # fetched_at = 1/1（確定ライン以前、TTL超過）
        fetched_at_before = make_dt(2026, 1, 1)
        now_after_ttl = fetched_at_before + timedelta(hours=25)
        status = policy.evaluate(2025, 12, fetched_at_before, now_after_ttl)
        assert status == FetchStatus.NEEDS_REFRESH
