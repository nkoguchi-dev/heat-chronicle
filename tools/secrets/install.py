"""Install the official, checksum-pinned Gitleaks release into an explicit directory."""

import argparse
import hashlib
import io
import json
import platform
import tarfile
import urllib.request
from pathlib import Path


def install(directory):
    config = json.loads(Path(__file__).with_name("version.json").read_text())
    system = platform.system().lower()
    machine = {"arm64": "arm64", "aarch64": "arm64", "x86_64": "x64"}.get(
        platform.machine()
    )
    target = f"{system}_{machine}"
    if target not in config["archives"]:
        raise ValueError("No reviewed Gitleaks archive for this platform")
    version = config["version"]
    url = f"https://github.com/gitleaks/gitleaks/releases/download/v{version}/gitleaks_{version}_{target}.tar.gz"
    with urllib.request.urlopen(url, timeout=60) as response:
        archive = response.read()
    if hashlib.sha256(archive).hexdigest() != config["archives"][target]:
        raise ValueError("Gitleaks archive checksum mismatch")
    directory.mkdir(parents=True, exist_ok=True)
    with tarfile.open(fileobj=io.BytesIO(archive)) as package:
        # Only the executable is written; archive paths are never extracted.
        member = package.extractfile("gitleaks")
        if member is None:
            raise ValueError("Missing Gitleaks executable")
        binary = directory / "gitleaks"
        binary.write_bytes(member.read())
        binary.chmod(0o755)
    print(f"Installed verified Gitleaks {version}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--bin-dir", type=Path, required=True)
    install(parser.parse_args().bin_dir.resolve())
