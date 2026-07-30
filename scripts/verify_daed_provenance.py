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


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--packageinfo", type=pathlib.Path, required=True)
    parser.add_argument("--lock", type=pathlib.Path, required=True)
    parser.add_argument("--makefile", type=pathlib.Path, required=True)
    parser.add_argument("--build-log", type=pathlib.Path)
    args = parser.parse_args()

    try:
        lock = json.loads(args.lock.read_text(encoding="utf-8"))
        expected = lock["daede"]["package_version"]
        makefile = makefile_version(args.makefile)
        registered = packageinfo_version(args.packageinfo)
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

    print(f"PASS: immutable DAED {expected} is registered and selected")
    return 0


if __name__ == "__main__":
    sys.exit(main())
