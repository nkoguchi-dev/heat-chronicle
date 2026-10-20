"""Build the relay reproducibly; AWS Python runtime supplies boto3."""

from pathlib import Path
from zipfile import ZipFile, ZipInfo

root = Path(__file__).resolve().parent
with ZipFile(root / "relay.zip", "w") as archive:
    archive.writestr(
        ZipInfo("relay.py", (2026, 1, 1, 0, 0, 0)), (root / "relay.py").read_bytes()
    )
