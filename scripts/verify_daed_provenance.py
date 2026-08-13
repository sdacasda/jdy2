#!/usr/bin/env python3
"""Verify that OpenWrt registered and built the immutable DAED package."""

from __future__ import annotations

import argparse
import json
import pathlib
import re
import sys


ASSIGNMENT_RE = re.compile(r"^(PKG_VERSION|PKG_RELEASE):=(.+)$", re.MULTILINE)


def makefile_version(path: pathlib.Path) -> str:
    assignments = dict(ASSIGNMENT_RE.findall(path.read_text(encoding="utf-8")))
    try:
        return f"{assignments['PKG_VERSION'].strip()}-r{assignments['PKG_RELEASE'].strip()}"
    except KeyError as exc:
        raise ValueError(f"missing {exc.args[0]} in {path}") from exc


def packageinfo_version(path: pathlib.Path) -> str:
    for block in path.read_text(encoding="utf-8").split("@@"):
        fields: dict[str, str] = {}
        for line in block.splitlines():
            if ": " in line:
                key, value = line.split(": ", 1)
                fields[key] = value
        if fields.get("Package") == "daed":
            if "Version" not in fields:
                raise ValueError("registered daed package has no Version field")
            return fields["Version"]
    raise ValueError("registered package metadata has no daed package")


def read_json_record(path: pathlib.Path, name: str) -> dict[str, object]:
    try:
        record = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ValueError(f"cannot read {name}: {exc}") from exc
    if not isinstance(record, dict):
        raise ValueError(f"{name} must be a JSON object")
    return record


def verify_source_provenance(args: argparse.Namespace) -> None:
    records = (args.assembly_manifest, args.archive_provenance, args.static_web_provenance)
    if not any(records):
        return
    if not all(records):
        raise ValueError("assembly, archive, and static-Web provenance must be supplied together")
    assembly = read_json_record(args.assembly_manifest, "assembly manifest")
    archive = read_json_record(args.archive_provenance, "archive provenance")
    static_web = read_json_record(args.static_web_provenance, "static-Web provenance")
    pins = assembly.get("pins")
    if not isinstance(pins, dict):
        raise ValueError("assembly manifest has no immutable pins")
    for key in ("WEB_PATCH_SHA256", "DATABASE_PATCH_SHA256"):
        value = pins.get(key)
        if not isinstance(value, str) or not re.fullmatch(r"[0-9a-f]{64}", value):
            raise ValueError(f"assembly manifest has invalid {key}")
    digest = assembly.get("sha256")
    size = assembly.get("size")
    source_root = assembly.get("source_root")
    if not isinstance(digest, str) or not re.fullmatch(r"[0-9a-f]{64}", digest):
        raise ValueError("assembly manifest has invalid archive digest")
    if not isinstance(size, int) or size <= 0 or not isinstance(source_root, str) or not source_root:
        raise ValueError("assembly manifest has incomplete archive provenance")
    if archive.get("sha256") != digest or archive.get("size") != size:
        raise ValueError("installed archive provenance does not match assembly manifest")
    if static_web.get("archive_sha256") != digest or static_web.get("root") != source_root:
        raise ValueError("static-Web provenance does not match assembled archive")
    static_digest = static_web.get("tree_sha256")
    if not isinstance(static_digest, str) or not re.fullmatch(r"[0-9a-f]{64}", static_digest):
        raise ValueError("static-Web provenance has invalid tree digest")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--packageinfo", type=pathlib.Path, required=True)
    parser.add_argument("--lock", type=pathlib.Path, required=True)
    parser.add_argument("--makefile", type=pathlib.Path, required=True)
    parser.add_argument("--build-log", type=pathlib.Path)
    parser.add_argument("--assembly-manifest", type=pathlib.Path)
    parser.add_argument("--archive-provenance", type=pathlib.Path)
    parser.add_argument("--static-web-provenance", type=pathlib.Path)
    args = parser.parse_args()

    try:
        lock = json.loads(args.lock.read_text(encoding="utf-8"))
        expected = lock["daede"]["package_version"]
        makefile = makefile_version(args.makefile)
        registered = packageinfo_version(args.packageinfo)
        verify_source_provenance(args)
    except (OSError, ValueError, KeyError, json.JSONDecodeError) as exc:
        print(f"FAIL: cannot verify DAED provenance: {exc}")
        return 1

    if makefile != expected:
        print(f"FAIL: locked DAED Makefile is {makefile}; expected {expected}")
        return 1
    if registered != expected:
        print(f"FAIL: registered DAED is {registered}; expected {expected}")
        return 1

    if args.build_log is not None:
        try:
            build_log = args.build_log.read_text(encoding="utf-8", errors="replace")
        except OSError as exc:
            print(f"FAIL: cannot read DAED build log: {exc}")
            return 1
        if "feeds/packages/net/daed" in build_log:
            print("FAIL: build log shows the conflicting feed DAED package")
            return 1
        if not re.search(r"Entering directory '.*/package/custom/daed'", build_log):
            print("FAIL: build log does not prove package/custom/daed was compiled")
            return 1

    print(f"PASS: immutable DAED {expected} is registered, source-bound, and selected")
    return 0


if __name__ == "__main__":
    sys.exit(main())
