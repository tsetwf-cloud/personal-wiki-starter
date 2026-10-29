#!/usr/bin/env python3
"""Build the allowlisted installable Personal Wiki skill and release ZIP."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import shutil
import zipfile

ROOT = Path(__file__).resolve().parents[1]
CONFIG = ROOT / "distribution-files.json"
PACKAGE = ROOT / "skills" / "personal-wiki"


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def build(output: Path | None) -> dict[str, object]:
    config = json.loads(CONFIG.read_text(encoding="utf-8"))
    files: list[str] = config["files"]
    version: str = config["version"]

    if PACKAGE.exists():
        shutil.rmtree(PACKAGE)
    PACKAGE.mkdir(parents=True)

    hashes: dict[str, str] = {}
    for relative in files:
        source = ROOT / relative
        if not source.is_file() or source.is_symlink():
            raise SystemExit(f"invalid distribution source: {relative}")
        target = PACKAGE / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, target)
        hashes[relative] = sha256(source)

    manifest = {"version": version, "files": files, "sha256": hashes}
    (PACKAGE / "distribution-manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )

    zip_hash = None
    if output:
        output.parent.mkdir(parents=True, exist_ok=True)
        output.unlink(missing_ok=True)
        with zipfile.ZipFile(output, "w", zipfile.ZIP_DEFLATED) as archive:
            for path in sorted(PACKAGE.rglob("*")):
                if path.is_file():
                    archive.write(path, Path("personal-wiki") / path.relative_to(PACKAGE))
        with zipfile.ZipFile(output) as archive:
            if archive.testzip() is not None:
                raise SystemExit("release ZIP failed CRC validation")
        zip_hash = sha256(output)

    return {
        "status": "ok",
        "version": version,
        "package": str(PACKAGE.relative_to(ROOT)),
        "file_count": len(files) + 1,
        "zip": str(output) if output else None,
        "zip_sha256": zip_hash,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    output = args.output.resolve() if args.output else None
    print(json.dumps(build(output), ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
