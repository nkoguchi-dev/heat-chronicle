import json
from dataclasses import FrozenInstanceError
from pathlib import Path

import pytest

from app.domain.prefecture.catalog import PREFECTURES
from app.domain.prefecture.model import Prefecture


def test_catalog_preserves_all_region_numbers_names_and_order() -> None:
    # Snapshot from the pre-migration public catalog, independent of runtime data.
    expected = json.loads(
        (Path(__file__).parents[1] / "fixtures/prefectures.json").read_text()
    )
    assert [
        {"prec_no": item.prec_no, "name": item.name} for item in PREFECTURES
    ] == expected
    assert len(PREFECTURES) == len({item.prec_no for item in PREFECTURES}) == 61


def test_catalog_and_its_entries_are_immutable() -> None:
    assert isinstance(PREFECTURES, tuple)
    assert all(type(item) is Prefecture for item in PREFECTURES)
    with pytest.raises(FrozenInstanceError):
        setattr(PREFECTURES[0], "name", "changed")
    assert PREFECTURES[0] == Prefecture(11, "宗谷地方")
