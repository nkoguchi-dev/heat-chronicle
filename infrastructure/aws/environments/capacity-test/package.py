"""Build a deterministic fixture archive without third-party dependencies."""

from pathlib import Path
from zipfile import ZipFile, ZipInfo

root = Path(__file__).resolve().parent
with ZipFile(root / "fixture.zip", "w") as archive:
    archive.writestr(
        ZipInfo("fixture.py", (2026, 1, 1, 0, 0, 0)), (root / "fixture.py").read_bytes()
    )
