#!/usr/bin/env python3
"""Credential-safe scanner for the public source archive."""

from __future__ import annotations

import argparse
import pathlib
import re
import sys


PATTERNS = (
    ("node link", re.compile(r"\b(?:vless|vmess|trojan|hysteria2?|tuic|ss)://", re.I)),
    ("private key", re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----")),
    ("secret assignment", re.compile(r"\b(?:token|password|passwd|private_key)\s*[:=]\s*['\"]?[A-Za-z0-9+/=_-]{12,}", re.I)),
    ("public DAED listener", re.compile(r"(?:listen_addr\s*=\s*['\"]0\.0\.0\.0:2023|--listen\s+0\.0\.0\.0:2023)")),
)
SKIP_PARTS = {".git", "__pycache__", "firmware", "build_dir", "staging_dir", "dl"}
SKIP_SUFFIXES = {".zip", ".gz", ".bin", ".itb", ".pyc", ".png", ".jpg", ".jpeg", ".db"}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=pathlib.Path, default=pathlib.Path("."))
    args = parser.parse_args()
    root = args.root.resolve()
    findings: list[tuple[pathlib.Path, int, str]] = []

    for path in root.rglob("*"):
        if not path.is_file() or SKIP_PARTS.intersection(path.parts) or path.suffix.lower() in SKIP_SUFFIXES:
            continue
        if "superpowers" in path.parts:
            # Approved design/plan documents intentionally describe rejected
            # credential forms and unsafe listener examples.
            continue
        try:
            lines = path.read_text(encoding="utf-8").splitlines()
        except (UnicodeDecodeError, OSError):
            continue
        relative = path.relative_to(root)
        for number, line in enumerate(lines, 1):
            if "SECURITY-SCAN-ALLOW" in line:
                continue
            for label, pattern in PATTERNS:
                if pattern.search(line):
                    findings.append((relative, number, label))

    if findings:
        for path, number, label in findings:
            print(f"FAIL: {path}:{number}: possible {label} (value redacted)")
        return 1
    print("PASS: no public-source credential patterns found")
    return 0


if __name__ == "__main__":
    sys.exit(main())
