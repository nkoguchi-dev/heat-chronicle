class MockJmaClient:
    """JmaClient のモック。デフォルトではエラーを投げ、テストごとにレスポンスを設定する。"""

    def __init__(self) -> None:
        self.responses: dict[tuple[int, int], str] = {}

    async def fetch_daily_page(
        self,
        prec_no: int,
        block_no: str,
        year: int,
        month: int,
        station_type: str,
    ) -> str:
        key = (year, month)
        if key in self.responses:
            return self.responses[key]
        raise RuntimeError(f"MockJmaClient: 未設定のリクエスト ({year}-{month:02d})")

    async def close(self) -> None:
        pass

    def set_response(self, year: int, month: int, html: str) -> None:
        """テストから呼び出してモックレスポンスを設定する。"""
        self.responses[(year, month)] = html
