#!/usr/bin/env python3
"""Bind a cached DAED source archive to its pins and verify shipped Web assets."""

from __future__ import annotations

import argparse
import gzip
import hashlib
import json
import sys
import tarfile
from pathlib import Path, PurePosixPath

from install_daed_web import inspect_archive


ENDPOINT = b"/athena-daed/graphql"
MAX_WEB_ASSET_SIZE = 32 * 1024 * 1024


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def parse_pins(values: list[str]) -> dict[str, str]:
    pins: dict[str, str] = {}
    for value in values:
        key, separator, pin = value.partition("=")
        if not separator or not key or not pin or key in pins:
            raise RuntimeError(f"invalid or duplicate pin: {value!r}")
        pins[key] = pin
    if not pins:
        raise RuntimeError("at least one immutable pin is required")
    return dict(sorted(pins.items()))


def read_member(bundle: tarfile.TarFile, member: tarfile.TarInfo) -> bytes:
    if member.size > MAX_WEB_ASSET_SIZE:
        raise RuntimeError(f"Web asset is unexpectedly large: {member.name}")
    handle = bundle.extractfile(member)
    if handle is None:
        raise RuntimeError(f"unable to read archive member: {member.name}")
    data = handle.read(MAX_WEB_ASSET_SIZE + 1)
    if len(data) > MAX_WEB_ASSET_SIZE:
        raise RuntimeError(f"Web asset exceeds validation limit: {member.name}")
    if member.name.endswith(".gz"):
        try:
            data = gzip.decompress(data)
        except gzip.BadGzipFile as exc:
            raise RuntimeError(f"invalid compressed Web asset: {member.name}") from exc
        if len(data) > MAX_WEB_ASSET_SIZE:
            raise RuntimeError(f"expanded Web asset exceeds validation limit: {member.name}")
    return data


def verify_archive_contents(archive: Path) -> str:
    if not archive.is_file() or archive.stat().st_size == 0:
        raise RuntimeError(f"cache archive is missing or empty: {archive}")
    try:
        with tarfile.open(archive, "r:gz") as bundle:
            members = [member for member in bundle.getmembers() if member.isfile()]
            roots = {PurePosixPath(member.name).parts[0] for member in members}
            if len(roots) != 1:
                raise RuntimeError("cache archive must contain exactly one source root")
            root = next(iter(roots))
            names = {member.name for member in members}
            if f"{root}/wing/go.mod" not in names:
                raise RuntimeError("cache archive is missing wing/go.mod")
            if not any(
                name in names
                for name in (
                    f"{root}/wing/webrender/web/index.html",
                    f"{root}/wing/webrender/web/index.html.gz",
                )
            ):
                raise RuntimeError("cache archive is missing the embedded Web entry")

            source_name = f"{root}/apps/web/src/constants/default.ts"
            source = next((member for member in members if member.name == source_name), None)
            if source is None or ENDPOINT not in read_member(bundle, source):
                raise RuntimeError("cache archive is missing the source endpoint patch")

            embedded = False
            web_prefix = f"{root}/wing/webrender/web/"
            for member in members:
                if member.name.startswith(web_prefix) and ENDPOINT in read_member(bundle, member):
                    embedded = True
                    break
            if not embedded:
                raise RuntimeError("embedded Web bundle does not contain the same-origin endpoint")
            return root
    except (tarfile.TarError, OSError) as exc:
        raise RuntimeError(f"invalid DAED source cache archive: {exc}") from exc


def expected_record(
    archive: Path,
    cache_id: str,
    pins: dict[str, str],
    root: str,
    static_web: dict[str, object],
) -> dict:
    return {
        "schema_version": 2,
        "cache_id": cache_id,
        "source": archive.name,
        "source_root": root,
        "sha256": sha256_file(archive),
        "size": archive.stat().st_size,
        "pins": pins,
        "static_web": {
            "file_count": static_web["file_count"],
            "tree_sha256": static_web["tree_sha256"],
            "files": static_web["files"],
        },
    }


def write_manifest(path: Path, record: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(
        json.dumps(record, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    temporary.replace(path)


def verify_manifest(path: Path, expected: dict) -> None:
    if not path.is_file():
        raise RuntimeError(f"cache manifest is missing: {path}")
    try:
        actual = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise RuntimeError(f"cache manifest is invalid: {exc}") from exc
    if actual.get("sha256") != expected["sha256"]:
        raise RuntimeError("cache archive digest mismatch")
    if actual != expected:
        raise RuntimeError("cache manifest does not match the immutable assembly inputs")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--archive", type=Path, required=True)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--cache-id", required=True)
    parser.add_argument("--pin", action="append", default=[])
    parser.add_argument("--write", action="store_true")
    args = parser.parse_args()
    try:
        pins = parse_pins(args.pin)
        root = verify_archive_contents(args.archive)
        static_inspection = inspect_archive(args.archive)
        static_web = static_inspection["record"]
        if not isinstance(static_web, dict) or static_web.get("root") != root:
            raise RuntimeError("static Web source root does not match the DAED archive")
        expected = expected_record(
            args.archive, args.cache_id, pins, root, static_web
        )
        if args.write:
            write_manifest(args.manifest, expected)
        verify_manifest(args.manifest, expected)
    except Exception as exc:
        print(f"DAED source cache validation failed: {exc}", file=sys.stderr)
        return 1
    print(f"PASS: DAED source cache is bound to immutable pins ({args.cache_id})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
