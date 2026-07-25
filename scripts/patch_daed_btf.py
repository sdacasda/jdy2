#!/usr/bin/env python3
from __future__ import annotations

import re
import sys
from pathlib import Path


def patch_makefile(path: Path) -> None:
    text = path.read_text(encoding="utf-8")

    conditional = "+DAED_USE_VMLINUX_BTF:vmlinux-btf"
    count = text.count(conditional)
    if count != 1:
        raise RuntimeError(
            f"expected exactly one conditional vmlinux-btf dependency, found {count}"
        )

    text = text.replace(conditional, "+vmlinux-btf", 1)

    config_block = re.compile(
        r"\ndefine Package/daed/config\n.*?\nendef\n",
        flags=re.DOTALL,
    )
    text, removed = config_block.subn("\n", text, count=1)
    if removed != 1:
        raise RuntimeError(
            "unable to remove the DAED BTF choice block; upstream layout changed"
        )

    if "DAED_USE_KERNEL_BTF" in text or "DAED_USE_VMLINUX_BTF" in text:
        raise RuntimeError("DAED BTF choice symbols remain after patching")

    if "+vmlinux-btf" not in text:
        raise RuntimeError("unconditional vmlinux-btf dependency is missing")

    path.write_text(text, encoding="utf-8", newline="\n")


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
        print(f"DAED detached-BTF patch failed: {exc}", file=sys.stderr)
        return 1

    print(f"Patched DAED for unconditional detached BTF: {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
