"""Install only the reviewed Trivy executable from an official release archive."""

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
    target = {
        ("Linux", "x86_64"): "Linux-64bit",
        ("Darwin", "arm64"): "macOS-ARM64",
    }.get((platform.system(), platform.machine()))
    if target not in config["archives"]:
        raise ValueError("No reviewed Trivy archive for this platform")
    version = config["version"]
    url = f"https://github.com/aquasecurity/trivy/releases/download/v{version}/trivy_{version}_{target}.tar.gz"
    with urllib.request.urlopen(url, timeout=60) as response:
        archive = response.read()
    if hashlib.sha256(archive).hexdigest() != config["archives"][target]:
        raise ValueError("Trivy archive checksum mismatch")
    directory.mkdir(parents=True, exist_ok=True)
    with tarfile.open(fileobj=io.BytesIO(archive)) as package:
        member = package.extractfile("trivy")
        if member is None:
            raise ValueError("Missing Trivy executable")
        binary = directory / "trivy"
        binary.write_bytes(member.read())
        binary.chmod(0o755)
    print(f"Installed verified Trivy {version}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--bin-dir", type=Path, required=True)
    install(parser.parse_args().bin_dir.resolve())
