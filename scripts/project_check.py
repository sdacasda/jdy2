#!/usr/bin/env python3
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
errors: list[str] = []

required = [
    ".github/workflows/build-athena-ram-diagnostic.yml",
    "config/athena-ram-diagnostic.config",
    "scripts/inject_diagnostic.sh",
    "scripts/verify_config.sh",
    "scripts/collect_output.sh",
    "README.md",
    "PROJECT.json",
]

for rel in required:
    if not (ROOT / rel).is_file():
        errors.append(f"missing: {rel}")

project = json.loads((ROOT / "PROJECT.json").read_text(encoding="utf-8"))
if project.get("source_commit") != "cf9444c1b20458687898489b36e1aebf56d9baf2":
    errors.append("known-good source commit is not pinned")

cfg = (ROOT / "config/athena-ram-diagnostic.config").read_text(encoding="utf-8")
for token in [
    "CONFIG_TARGET_ROOTFS_INITRAMFS=y",
    "CONFIG_PACKAGE_dropbear=y",
    "CONFIG_PACKAGE_uhttpd=y",
    "# CONFIG_PACKAGE_daed is not set",
    "# CONFIG_PACKAGE_vmlinux-btf is not set",
]:
    if token not in cfg:
        errors.append(f"config safeguard missing: {token}")

workflow = (ROOT / ".github/workflows/build-athena-ram-diagnostic.yml").read_text(encoding="utf-8")
for token in [
    "cf9444c1b20458687898489b36e1aebf56d9baf2",
    "collect_output.sh",
    "No persistent firmware",
]:
    if token not in workflow:
        errors.append(f"workflow safeguard missing: {token}")

for path in ROOT.rglob("*"):
    if not path.is_file() or "__pycache__" in path.parts:
        continue
    data = path.read_bytes()
    if b"\r\n" in data:
        errors.append(f"CRLF: {path.relative_to(ROOT)}")
    text = data.decode("utf-8", errors="ignore")
    if re.search(r"^(<<<<<<< |=======\s*$|>>>>>>> )", text, re.MULTILINE):
        errors.append(f"merge marker: {path.relative_to(ROOT)}")

if errors:
    print("PROJECT CHECK FAILED", file=sys.stderr)
    for error in errors:
        print(f"- {error}", file=sys.stderr)
    raise SystemExit(1)

print("PROJECT CHECK PASSED")
