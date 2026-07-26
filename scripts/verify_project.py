#!/usr/bin/env python3
"""Validate the Athena v19 source tree before expensive build work."""

from __future__ import annotations

import argparse
import json
import pathlib
import re
import sys


SOURCE_NAMES = ("libwrt", "daede", "vmlinux_btf", "athena_led", "golang", "argon", "argon_config")
COMMIT_RE = re.compile(r"^[0-9a-f]{40}$")
BASE_REQUIRED = (
    "PROJECT.json",
    "SOURCES.lock.json",
    "docs/superpowers/specs/2026-07-25-athena-v19-design.md",
    "docs/superpowers/plans/2026-07-25-athena-v19-implementation.md",
)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=pathlib.Path, default=pathlib.Path("."))
    parser.add_argument("--allow-incomplete", action="store_true")
    args = parser.parse_args()
    root = args.root.resolve()
    errors: list[str] = []

    for relative in BASE_REQUIRED:
        if not (root / relative).is_file():
            errors.append(f"missing required file: {relative}")

    project_path = root / "PROJECT.json"
    if project_path.is_file():
        try:
            project = json.loads(project_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            errors.append(f"invalid PROJECT.json: {exc}")
        else:
            expectations = {
                "version": "v19.0.0-rc1",
                "target": "qualcommax/ipq60xx",
                "device": "jdcloud_re-cs-02",
                "lan_address": "192.168.50.1",
            }
            for key, expected in expectations.items():
                if project.get(key) != expected:
                    errors.append(f"PROJECT.json {key} must be {expected}")

    lock_path = root / "SOURCES.lock.json"
    if lock_path.is_file():
        try:
            lock = json.loads(lock_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            errors.append(f"invalid SOURCES.lock.json: {exc}")
        else:
            for name in SOURCE_NAMES:
                entry = lock.get(name)
                if not isinstance(entry, dict):
                    errors.append(f"missing source lock: {name}")
                    continue
                repository, commit = entry.get("repository", ""), entry.get("commit", "")
                if not isinstance(repository, str) or not repository.startswith("https://github.com/"):
                    errors.append(f"{name}: repository must be an HTTPS GitHub URL")
                if not isinstance(commit, str) or not COMMIT_RE.fullmatch(commit):
                    errors.append(f"{name}: commit must be a 40-character commit")

    if not args.allow_incomplete:
        for relative in (
            ".github/workflows/build-athena-v19.yml",
            "config/athena-v19.config",
            "packages/athena-runtime/Makefile",
            "packages/luci-app-athena/Makefile",
        ):
            if not (root / relative).is_file():
                errors.append(f"missing v19 implementation file: {relative}")
        for relative in (
            ".github/workflows/build-athena-final-candidate.yml",
            "config/athena-final-candidate.config",
        ):
            if (root / relative).exists():
                errors.append(f"legacy v18 path remains: {relative}")

    for path in root.rglob("*"):
        if not path.is_file() or ".git" in path.parts or path.suffix in {".zip", ".bin", ".itb", ".pyc"}:
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except (UnicodeDecodeError, OSError):
            continue
        relative = path.relative_to(root)
        placeholder_implementation = (
            "tests" in path.parts
            or path.name in {"verify_templates.py", "templates.sh"}
        )
        if path.suffix != ".tpl" and "docs" not in path.parts and not placeholder_implementation and re.search(r"\{\{[A-Z0-9_]+\}\}", text):
            errors.append(f"unresolved template variable outside .tpl: {relative}")
        if "\r\n" in text:
            errors.append(f"CRLF line endings: {relative}")
        if re.search(r"^(<<<<<<<|=======|>>>>>>>)", text, re.MULTILINE):
            errors.append(f"merge marker: {relative}")

    if errors:
        for error in errors:
            print(f"FAIL: {error}")
        return 1
    print("PASS: Athena v19 project structure is valid")
    return 0


if __name__ == "__main__":
    sys.exit(main())
