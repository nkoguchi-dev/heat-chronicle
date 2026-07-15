from app.domain.station.model import Station
from app.domain.temperature.model import DailyTemperature
from app.infrastructure.scraper.jma_parser import parse_daily_page


class MockTemperatureDataSource:
    """気象データ取得Portのモック。テストごとにJMA HTMLを設定する。"""

    def __init__(self) -> None:
        self.responses: dict[tuple[int, int], str] = {}

    async def fetch_daily_temperatures(
        self,
        station: Station,
        year: int,
        month: int,
    ) -> list[DailyTemperature]:
        key = (year, month)
        if key in self.responses:
            return parse_daily_page(
                self.responses[key],
                year,
                month,
                station.station_type,
            )
        raise RuntimeError(
            f"MockTemperatureDataSource: 未設定のリクエスト " f"({year}-{month:02d})"
        )

    def set_response(self, year: int, month: int, html: str) -> None:
        """テストから呼び出してモックレスポンスを設定する。"""
        self.responses[(year, month)] = html
