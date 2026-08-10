#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import re
import shutil
import sys
from pathlib import Path


SOURCE_RE = re.compile(r"^PKG_SOURCE:=(\S+)\s*$", re.MULTILINE)
HASH_RE = re.compile(r"^PKG_HASH:=[0-9a-fA-F]{64}\s*$", re.MULTILINE)


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def install(makefile: Path, archive: Path, dl_dir: Path, provenance: Path) -> None:
    if not makefile.is_file():
        raise RuntimeError(f"DAED Makefile is missing: {makefile}")
    if not archive.is_file() or archive.stat().st_size == 0:
        raise RuntimeError(f"DAED source archive is missing or empty: {archive}")

    text = makefile.read_text(encoding="utf-8")
    source_matches = SOURCE_RE.findall(text)
    hash_matches = HASH_RE.findall(text)
    if len(source_matches) != 1:
        raise RuntimeError(f"expected one PKG_SOURCE, found {len(source_matches)}")
    if len(hash_matches) != 1:
        raise RuntimeError(f"expected one PKG_HASH, found {len(hash_matches)}")

    source_name = source_matches[0]
    if archive.name != source_name:
        raise RuntimeError(
            f"archive name does not match PKG_SOURCE: {archive.name} != {source_name}"
        )

    digest = sha256_file(archive)
    patched = HASH_RE.sub(f"PKG_HASH:={digest}", text, count=1)
    makefile.write_text(patched, encoding="utf-8", newline="\n")

    dl_dir.mkdir(parents=True, exist_ok=True)
    destination = dl_dir / source_name
    if archive.resolve() != destination.resolve():
        temporary = destination.with_suffix(destination.suffix + ".tmp")
        shutil.copyfile(archive, temporary)
        temporary.replace(destination)
    if sha256_file(destination) != digest:
        raise RuntimeError("installed DAED source archive checksum mismatch")

    provenance.parent.mkdir(parents=True, exist_ok=True)
    provenance.write_text(
        json.dumps(
            {
                "source": source_name,
                "sha256": digest,
                "size": destination.stat().st_size,
                "origin": "locally assembled from immutable component commits",
            },
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
        newline="\n",
    )


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Install a locally assembled DAED source archive into OpenWrt dl"
    )
    parser.add_argument("--makefile", type=Path, required=True)
    parser.add_argument("--archive", type=Path, required=True)
    parser.add_argument("--dl-dir", type=Path, required=True)
    parser.add_argument("--provenance", type=Path, required=True)
    args = parser.parse_args()
    try:
        install(args.makefile, args.archive, args.dl_dir, args.provenance)
    except Exception as exc:
        print(f"DAED source installation failed: {exc}", file=sys.stderr)
        return 1
    print(f"Installed DAED source: {args.archive.name}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
