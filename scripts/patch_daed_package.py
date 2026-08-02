#!/usr/bin/env python3
from __future__ import annotations

import re
import sys
from pathlib import Path


HOOK = "\tpython3 $(CURDIR)/files/patch_daed_web.py $(DAED_BUILD_DIR)"
BUILD_PREPARE = re.compile(
    r"(^define Build/Prepare\n)(.*?)(^endef\s*$)",
    flags=re.DOTALL | re.MULTILINE,
)


def patch_makefile(path: Path) -> None:
    if not path.is_file():
        raise RuntimeError(f"DAED Makefile is missing: {path}")

    text = path.read_text(encoding="utf-8")
    hook_count = text.count(HOOK)
    blocks = list(BUILD_PREPARE.finditer(text))

    if hook_count == 1:
        if len(blocks) == 1 and HOOK in blocks[0].group(2):
            return
        raise RuntimeError(
            f"unexpected DAED package hook layout: blocks={len(blocks)} hooks={hook_count}"
        )
    if hook_count != 0 or len(blocks) != 1:
        raise RuntimeError(
            f"unexpected DAED package layout: blocks={len(blocks)} hooks={hook_count}"
        )

    block = blocks[0]
    body = block.group(2)
    if body and not body.endswith("\n"):
        body += "\n"
    replacement = block.group(1) + body + HOOK + "\n" + block.group(3)
    patched = text[: block.start()] + replacement + text[block.end() :]
    if patched.count(HOOK) != 1:
        raise RuntimeError("DAED package hook insertion was not unique")
    path.write_text(patched, encoding="utf-8", newline="\n")


def main() -> int:
    if len(sys.argv) != 2:
        print(f"usage: {sys.argv[0]} DAED_MAKEFILE", file=sys.stderr)
        return 2

    path = Path(sys.argv[1])
    if not path.is_file():
        print(f"DAED Makefile not found: {path}", file=sys.stderr)
        return 2

    try:
        patch_makefile(path)
    except Exception as exc:
        print(f"DAED package Web hook patch failed: {exc}", file=sys.stderr)
        return 1

    print(f"Patched DAED package Web hook: {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
