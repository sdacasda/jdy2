#!/usr/bin/env python3
from __future__ import annotations

import sys
from pathlib import Path


SOURCE = Path("apps/web/src/constants/default.ts")
OLD = "export const DEFAULT_ENDPOINT_URL = `${location.protocol}//${location.hostname}:2023/graphql`"
NEW = "export const DEFAULT_ENDPOINT_URL = `${location.origin}/athena-daed/graphql`"


def patch_source(root: Path) -> None:
    path = root / SOURCE
    if not path.is_file():
        raise RuntimeError(f"DAED endpoint source is missing: {SOURCE}")

    text = path.read_text(encoding="utf-8")
    old_count = text.count(OLD)
    new_count = text.count(NEW)
    if (old_count, new_count) == (1, 0):
        path.write_text(text.replace(OLD, NEW, 1), encoding="utf-8", newline="\n")
        return
    if (old_count, new_count) == (0, 1):
        return
    raise RuntimeError(
        f"unexpected DAED endpoint source: old={old_count} new={new_count}"
    )


def main() -> int:
    if len(sys.argv) != 2:
        print(f"usage: {sys.argv[0]} DAED_SOURCE_ROOT", file=sys.stderr)
        return 2

    root = Path(sys.argv[1])
    if not root.is_dir():
        print(f"DAED source root not found: {root}", file=sys.stderr)
        return 2

    try:
        patch_source(root)
    except Exception as exc:
        print(f"DAED Web endpoint patch failed: {exc}", file=sys.stderr)
        return 1

    print(f"Patched DAED Web endpoint: {root / SOURCE}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
