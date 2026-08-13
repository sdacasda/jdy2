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
    ("subscription token", re.compile(r"\b(?:subscription(?:_token)?|subscribe|token)\s*[:=]\s*['\"]?[A-Za-z0-9+/=_-]{12,}", re.I)),
    ("realistic UUID", re.compile(r"\b(?!00000000-0000-0000-0000-000000000000\b)[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}\b", re.I)),
    ("GraphQL password variable", re.compile(r"\bvariables\b[^\n]{0,256}['\"]password['\"]\s*:", re.I)),
    ("DAED password value", re.compile(r"\bDAED\s+Password\s*[:=]\s*\S+", re.I)),
    ("DAED sentinel", re.compile("SENTINEL_" + "DAED_PASSWORD_DO_NOT_RENDER")),
    ("secret assignment", re.compile(r"\b(?:token|password|passwd|private_key)\s*[:=]\s*['\"]?[A-Za-z0-9+/=_-]{12,}", re.I)),
    ("public DAED listener", re.compile(r"(?:listen_addr\s*=\s*['\"]0\.0\.0\.0:2023|--listen\s+0\.0\.0\.0:2023)")),
)
SKIP_PARTS = {".git", "__pycache__", "firmware", "build_dir", "staging_dir", "dl"}
SKIP_SUFFIXES = {".zip", ".gz", ".bin", ".itb", ".pyc", ".png", ".jpg", ".jpeg", ".db"}
KNOWN_TEST_FIXTURE_LINES = {
    (
        pathlib.Path("tests/runtime/test_common.sh"),
        "printf '%s\\n' 'v" + "less://user@example.com " + "to" + "ken=abcdef123456' | # SECURITY-SCAN-ALLOW",
    ),
}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=pathlib.Path, default=pathlib.Path("."))
    args = parser.parse_args()
    root = args.root.resolve()
    findings: list[tuple[pathlib.Path, int, str]] = []

    for path in root.rglob("*"):
        relative = path.relative_to(root)
        if not path.is_file() or SKIP_PARTS.intersection(relative.parts) or path.suffix.lower() in SKIP_SUFFIXES:
            continue
        if ".superpowers" in relative.parts or (
            len(relative.parts) >= 2
            and relative.parts[0] == "docs"
            and relative.parts[1] == "superpowers"
        ):
            # Local planning and historical specifications are not release
            # inputs. Do not exempt tracked production, tests, or other docs.
            continue
        try:
            lines = path.read_text(encoding="utf-8").splitlines()
        except (UnicodeDecodeError, OSError):
            continue
        for number, line in enumerate(lines, 1):
            if (relative, line) in KNOWN_TEST_FIXTURE_LINES:
                continue
            for label, pattern in PATTERNS:
                sentinel_test_paths = {
                    pathlib.Path("scripts/install_daed_web.py"),
                    pathlib.Path("scripts/tests/fixtures/daed_web/graphql-request-error.json"),
                    pathlib.Path("tests/test_daed_static_web.py"),
                    pathlib.Path("tests/test_daed_web_patch.py"),
                }
                if label == "DAED sentinel" and relative in sentinel_test_paths:
                    continue
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
