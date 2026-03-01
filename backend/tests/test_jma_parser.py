from datetime import date
from typing import Any

from app.infrastructure.scraper.jma_parser import (
    DailyRecord,
    _parse_temp,
    parse_daily_page,
)


class TestParseTemp:
    def test_normal_value(self) -> None:
        assert _parse_temp("25.3") == 25.3

    def test_negative_value(self) -> None:
        assert _parse_temp("-5.2") == -5.2

    def test_missing_dash(self) -> None:
        assert _parse_temp("--") is None

    def test_missing_x(self) -> None:
        assert _parse_temp("×") is None

    def test_missing_slash(self) -> None:
        assert _parse_temp("///") is None

    def test_empty_string(self) -> None:
        assert _parse_temp("") is None

    def test_quality_flag_bracket(self) -> None:
        assert _parse_temp("25.3]") == 25.3

    def test_quality_flag_paren(self) -> None:
        assert _parse_temp("25.3)") == 25.3

    def test_quality_flag_star(self) -> None:
        assert _parse_temp("25.3*") == 25.3

    def test_quality_flag_hash(self) -> None:
        assert _parse_temp("25.3#") == 25.3

    def test_whitespace(self) -> None:
        assert _parse_temp("  25.3  ") == 25.3


class TestParseDailyPage:
    def _make_s1_html(self, rows: list[tuple[Any, ...]]) -> str:
        """Build a minimal daily_s1 HTML table.

        rows: list of (day, c1..c5, avg_temp, max_temp, min_temp, ...)
        """
        row_html = ""
        for row in rows:
            cells = "".join(f"<td>{v}</td>" for v in row)
            row_html += f'<tr class="mtx">{cells}</tr>'
        return f"""
        <html><body>
        <table class="data2_s">
        <tbody>
        <tr class="mtx"><th>日</th></tr>
        {row_html}
        </tbody>
        </table>
        </body></html>
        """

    def test_parse_normal_row(self) -> None:
        # day, 5 extra cols, avg, max, min
        html = self._make_s1_html([(1, "x", "x", "x", "x", "x", "5.0", "10.0", "0.5")])
        records = parse_daily_page(html, 2024, 1, "s")
        assert len(records) == 1
        assert records[0] == DailyRecord(
            date=date(2024, 1, 1),
            max_temp=10.0,
            min_temp=0.5,
            avg_temp=5.0,
        )

    def test_parse_missing_data(self) -> None:
        html = self._make_s1_html([(1, "x", "x", "x", "x", "x", "--", "--", "--")])
        records = parse_daily_page(html, 2024, 1, "s")
        assert len(records) == 1
        assert records[0].max_temp is None
        assert records[0].min_temp is None
        assert records[0].avg_temp is None

    def test_parse_quality_flags(self) -> None:
        html = self._make_s1_html(
            [(1, "x", "x", "x", "x", "x", "5.0]", "10.0)", "0.5#")]
        )
        records = parse_daily_page(html, 2024, 1, "s")
        assert records[0].max_temp == 10.0
        assert records[0].min_temp == 0.5
        assert records[0].avg_temp == 5.0

    def test_empty_table(self) -> None:
        html = (
            '<html><body><table class="data2_s"><tbody></tbody></table></body></html>'
        )
        records = parse_daily_page(html, 2024, 1, "s")
        assert records == []

    def test_no_table(self) -> None:
        html = "<html><body><p>No data</p></body></html>"
        records = parse_daily_page(html, 2024, 1, "s")
        assert records == []

    def test_invalid_day_skipped(self) -> None:
        html = self._make_s1_html(
            [("合計", "x", "x", "x", "x", "x", "5.0", "10.0", "0.5")]
        )
        records = parse_daily_page(html, 2024, 1, "s")
        assert records == []

    def _make_a1_html(self, rows: list[tuple[Any, ...]]) -> str:
        """Build a minimal daily_a1 HTML table."""
        row_html = ""
        for row in rows:
            cells = "".join(f"<td>{v}</td>" for v in row)
            row_html += f'<tr class="mtx">{cells}</tr>'
        return f"""
        <html><body>
        <table class="data2_s">
        <tbody>
        {row_html}
        </tbody>
        </table>
        </body></html>
        """

    def test_parse_amedas_row(self) -> None:
        # day, 3 extra cols, avg, max, min
        html = self._make_a1_html([(1, "x", "x", "x", "5.0", "10.0", "0.5")])
        records = parse_daily_page(html, 2024, 1, "a")
        assert len(records) == 1
        assert records[0].max_temp == 10.0
        assert records[0].min_temp == 0.5
