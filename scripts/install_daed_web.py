#!/usr/bin/env python3
"""Install the original DAED Web build from a verified source archive."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import re
import shutil
import sys
import tarfile
import tempfile
from urllib.parse import urlsplit
import uuid


GRAPHQL_ENDPOINT = b"/athena-daed/graphql"
FORBIDDEN_BROWSER_ENDPOINTS = (
    b":2023/graphql",
    b"127.0.0.1:2023",
    b"192.168.50.1:2023",
)
MAX_STATIC_FILE_SIZE = 64 * 1024 * 1024
ASSET_REFERENCE = re.compile(r"(?:src|href)=[\"']([^\"']+)[\"']", re.I)
IMAGE_SUFFIXES = {".avif", ".gif", ".ico", ".jpeg", ".jpg", ".png", ".svg", ".webp"}


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def normalized_member_path(name: str) -> PurePosixPath:
    if not name or "\\" in name or name.startswith("/"):
        raise RuntimeError(f"unsafe archive path: {name!r}")
    stripped = name[:-1] if name.endswith("/") else name
    components = stripped.split("/")
    if not stripped or any(part in {"", ".", ".."} for part in components):
        raise RuntimeError(f"unsafe archive path: {name!r}")
    return PurePosixPath(*components)


def _read_member(bundle: tarfile.TarFile, member: tarfile.TarInfo) -> bytes:
    if member.size < 0 or member.size > MAX_STATIC_FILE_SIZE:
        raise RuntimeError(f"DAED static Web asset has invalid size: {member.name}")
    handle = bundle.extractfile(member)
    if handle is None:
        raise RuntimeError(f"unable to read DAED static Web asset: {member.name}")
    payload = handle.read(MAX_STATIC_FILE_SIZE + 1)
    if len(payload) > MAX_STATIC_FILE_SIZE or len(payload) != member.size:
        raise RuntimeError(f"DAED static Web asset size mismatch: {member.name}")
    return payload


def _local_references(index_html: bytes) -> list[str]:
    try:
        text = index_html.decode("utf-8", errors="strict")
    except UnicodeDecodeError as exc:
        raise RuntimeError("DAED static Web index.html is not UTF-8") from exc
    references: list[str] = []
    for value in ASSET_REFERENCE.findall(text):
        if value.startswith(("http://", "https://", "//")):
            raise RuntimeError(f"DAED static Web index has an external asset: {value}")
        if not value.startswith("./"):
            continue
        path = urlsplit(value).path[2:]
        normalized = normalized_member_path(path)
        references.append(normalized.as_posix())
    return sorted(set(references))


def _tree_record(
    archive: Path,
    root: str,
    payloads: dict[str, bytes],
) -> dict[str, object]:
    files = [
        {
            "path": path,
            "size": len(payloads[path]),
            "sha256": sha256_bytes(payloads[path]),
        }
        for path in sorted(payloads)
    ]
    digest = hashlib.sha256()
    for entry in files:
        digest.update(entry["path"].encode("utf-8"))
        digest.update(b"\0")
        digest.update(entry["sha256"].encode("ascii"))
        digest.update(b"\n")
    return {
        "schema": 1,
        "archive": archive.name,
        "archive_sha256": hashlib.sha256(archive.read_bytes()).hexdigest(),
        "root": root,
        "file_count": len(files),
        "tree_sha256": digest.hexdigest(),
        "files": files,
    }


def inspect_archive(archive: Path) -> dict[str, object]:
    if not archive.is_file() or archive.stat().st_size == 0:
        raise RuntimeError(f"DAED source archive is missing or empty: {archive}")
    try:
        with tarfile.open(archive, "r:gz") as bundle:
            members = bundle.getmembers()
            normalized: list[tuple[tarfile.TarInfo, PurePosixPath]] = []
            seen: set[str] = set()
            roots: set[str] = set()
            for member in members:
                path = normalized_member_path(member.name)
                key = path.as_posix()
                if key in seen:
                    raise RuntimeError(f"duplicate archive path: {member.name}")
                seen.add(key)
                roots.add(path.parts[0])
                normalized.append((member, path))
            if len(roots) != 1:
                raise RuntimeError("DAED source archive must contain exactly one root")
            root = next(iter(roots))
            prefix = PurePosixPath(root, "apps", "web", "dist")
            payloads: dict[str, bytes] = {}
            for member, path in normalized:
                try:
                    relative = path.relative_to(prefix)
                except ValueError:
                    continue
                if not relative.parts:
                    continue
                if member.isdir():
                    continue
                if not member.isfile():
                    raise RuntimeError(
                        f"unsupported archive member under DAED static Web: {member.name}"
                    )
                relative_name = relative.as_posix()
                if relative_name in payloads:
                    raise RuntimeError(f"duplicate DAED static Web asset: {relative_name}")
                payloads[relative_name] = _read_member(bundle, member)
    except (OSError, tarfile.TarError) as exc:
        raise RuntimeError(f"invalid DAED source archive: {exc}") from exc

    index = payloads.get("index.html")
    if index is None:
        raise RuntimeError("DAED static Web index.html is missing")
    references = _local_references(index)
    for reference in references:
        if reference not in payloads:
            raise RuntimeError(f"DAED static Web referenced asset is missing: {reference}")
    if not any(PurePosixPath(path).suffix.lower() == ".js" for path in references):
        raise RuntimeError("DAED static Web index.html does not reference JavaScript")
    if not any(PurePosixPath(path).suffix.lower() == ".css" for path in references):
        raise RuntimeError("DAED static Web index.html does not reference a stylesheet")
    if not any(PurePosixPath(path).suffix.lower() in IMAGE_SUFFIXES for path in references):
        raise RuntimeError("DAED static Web index.html does not reference a logo")

    browser_assets = b"\n".join(
        payload
        for path, payload in payloads.items()
        if PurePosixPath(path).suffix.lower() in {".html", ".js", ".mjs"}
    )
    if any(value in browser_assets for value in FORBIDDEN_BROWSER_ENDPOINTS):
        raise RuntimeError("DAED static Web contains a browser-visible DAED port")
    if GRAPHQL_ENDPOINT not in browser_assets:
        raise RuntimeError("DAED static Web is missing the same-origin GraphQL endpoint")

    return {
        "record": _tree_record(archive, root, payloads),
        "payloads": payloads,
    }


def _write_json(path: Path, record: dict[str, object]) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.parent / f".{path.name}.{uuid.uuid4().hex}.tmp"
    temporary.write_text(
        json.dumps(record, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    return temporary


def install_static_web(
    archive: Path,
    destination: Path,
    provenance: Path,
) -> dict[str, object]:
    inspected = inspect_archive(archive)
    record = inspected["record"]
    payloads = inspected["payloads"]
    if not isinstance(record, dict) or not isinstance(payloads, dict):
        raise RuntimeError("internal DAED static Web inspection result is invalid")

    destination.parent.mkdir(parents=True, exist_ok=True)
    temporary = Path(
        tempfile.mkdtemp(prefix=f".{destination.name}.", dir=destination.parent)
    )
    provenance_temporary: Path | None = None
    destination_backup = destination.parent / f".{destination.name}.backup-{uuid.uuid4().hex}"
    provenance_backup = provenance.parent / f".{provenance.name}.backup-{uuid.uuid4().hex}"
    destination_moved = False
    provenance_moved = False
    try:
        for relative, payload in payloads.items():
            target = temporary.joinpath(*PurePosixPath(relative).parts)
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(payload)
            if sha256_bytes(target.read_bytes()) != sha256_bytes(payload):
                raise RuntimeError(f"DAED static Web write verification failed: {relative}")

        provenance_temporary = _write_json(provenance, record)
        if destination.exists():
            os.replace(destination, destination_backup)
            destination_moved = True
        if provenance.exists():
            os.replace(provenance, provenance_backup)
            provenance_moved = True
        os.replace(temporary, destination)
        os.replace(provenance_temporary, provenance)
        provenance_temporary = None
    except Exception:
        if destination.exists() and destination_moved:
            shutil.rmtree(destination, ignore_errors=True)
        if destination_moved and destination_backup.exists():
            os.replace(destination_backup, destination)
        if provenance.exists() and provenance_moved:
            provenance.unlink(missing_ok=True)
        if provenance_moved and provenance_backup.exists():
            os.replace(provenance_backup, provenance)
        raise
    finally:
        if temporary.exists():
            shutil.rmtree(temporary, ignore_errors=True)
        if provenance_temporary is not None:
            provenance_temporary.unlink(missing_ok=True)
        if destination_backup.exists():
            shutil.rmtree(destination_backup, ignore_errors=True)
        provenance_backup.unlink(missing_ok=True)
    return record


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--archive", type=Path, required=True)
    parser.add_argument("--destination", type=Path, required=True)
    parser.add_argument("--provenance", type=Path, required=True)
    args = parser.parse_args(argv)
    try:
        record = install_static_web(args.archive, args.destination, args.provenance)
    except Exception as exc:
        print(f"DAED static Web installation failed: {exc}", file=sys.stderr)
        return 1
    print(
        "PASS: installed DAED static Web "
        f"({record['file_count']} files, {record['tree_sha256']})"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
