from app.application.prefecture.list_prefecture_use_case import ListPrefectureUseCase
from app.application.prefecture.ports.inbound.list_prefecture import PrefectureOutput


def test_prefecture_output_preserves_catalog_and_order() -> None:
    output = ListPrefectureUseCase().list_prefectures()
    assert len(output) == 61
    assert len({item.prec_no for item in output}) == 61
    assert output[0] == PrefectureOutput(prec_no=11, name="宗谷地方")
    assert output[-1] == PrefectureOutput(prec_no=99, name="南極")
    assert PrefectureOutput(prec_no=44, name="東京都") in output


def test_caller_cannot_mutate_the_next_prefecture_result() -> None:
    use_case = ListPrefectureUseCase()
    output = use_case.list_prefectures()
    output.clear()
    assert len(use_case.list_prefectures()) == 61
