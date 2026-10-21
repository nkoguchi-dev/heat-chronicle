from app.application.prefecture.ports.inbound.list_prefecture import PrefectureOutput
from app.domain.prefecture.catalog import PREFECTURES


class ListPrefectureUseCase:
    def list_prefectures(self) -> list[PrefectureOutput]:
        return [
            PrefectureOutput(prec_no=prefecture.prec_no, name=prefecture.name)
            for prefecture in PREFECTURES
        ]
