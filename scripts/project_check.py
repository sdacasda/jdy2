#!/usr/bin/env python3
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
errors: list[str] = []

required_files = [
    ".github/workflows/build-athena-minimal-daed.yml",
    ".github/workflows/validate-project.yml",
    "config/athena-minimal.config",
    "scripts/prepare_packages.sh",
    "scripts/patch_daed_btf.py",
    "scripts/apply_defaults.sh",
    "scripts/verify_config.sh",
    "scripts/collect_output.sh",
    "scripts/verify_after_flash.sh",
    "README.md",
    "PROJECT.json",
    "docs/BUILD.md",
    "docs/FLASH.md",
]

for rel in required_files:
    if not (ROOT / rel).is_file():
        errors.append(f"missing required file: {rel}")

try:
    project = json.loads((ROOT / "PROJECT.json").read_text(encoding="utf-8"))
except Exception as exc:
    errors.append(f"PROJECT.json is invalid: {exc}")
    project = {}

expected_commit = "cf9444c1b20458687898489b36e1aebf56d9baf2"
if project.get("source_commit") != expected_commit:
    errors.append("PROJECT.json does not pin the known-good LiBwrt commit")

cfg_path = ROOT / "config/athena-minimal.config"
cfg = cfg_path.read_text(encoding="utf-8") if cfg_path.is_file() else ""

required_config = {
    "CONFIG_TARGET_qualcommax_ipq60xx_DEVICE_jdcloud_re-cs-02=y",
    "CONFIG_TARGET_ROOTFS_INITRAMFS=y",
    "CONFIG_PACKAGE_daed=y",
    "CONFIG_PACKAGE_luci-app-daede_daed=y",
    "CONFIG_PACKAGE_kmod-sched-bpf=y",
    "CONFIG_KERNEL_XDP_SOCKETS=y",
    "CONFIG_PACKAGE_vmlinux-btf=y",
    "CONFIG_PACKAGE_luci-app-athena-led=y",
}

for token in sorted(required_config):
    if token not in cfg:
        errors.append(f"missing config safeguard: {token}")

for forbidden in [
    "CONFIG_DAED_USE_VMLINUX_BTF=y",
    "CONFIG_KERNEL_DEBUG_INFO_BTF=y",
    "CONFIG_DAED_USE_KERNEL_BTF=y",
    "CONFIG_PACKAGE_luci-app-openclash=y",
    "CONFIG_PACKAGE_luci-app-passwall=y",
    "CONFIG_PACKAGE_luci-app-homeproxy=y",
    "CONFIG_PACKAGE_luci-app-dockerman=y",
    "CONFIG_PACKAGE_luci-app-samba4=y",
]:
    if re.search(rf"^{re.escape(forbidden)}$", cfg, re.MULTILINE):
        errors.append(f"forbidden config enabled: {forbidden}")

workflow_path = ROOT / ".github/workflows/build-athena-minimal-daed.yml"
workflow = workflow_path.read_text(encoding="utf-8") if workflow_path.is_file() else ""

for token in [
    "https://github.com/LiBwrt/openwrt-6.x.git",
    expected_commit,
    "KERNEL_SIZE_VALUE",
    "6291456",
    "athena-minimal.config",
    "collect_output.sh",
    "prepare_packages.sh",
]:
    if token not in workflow:
        errors.append(f"workflow safeguard missing: {token}")

prepare_path = ROOT / "scripts/prepare_packages.sh"
prepare_text = prepare_path.read_text(encoding="utf-8") if prepare_path.is_file() else ""
for token in [
    "patch_daed_btf.py",
    "grep -Fq '+vmlinux-btf'",
    "grep -q 'DAED_USE_'",
]:
    if token not in prepare_text:
        errors.append(f"detached-BTF package patch safeguard missing: {token}")

patcher_path = ROOT / "scripts/patch_daed_btf.py"
patcher_text = patcher_path.read_text(encoding="utf-8") if patcher_path.is_file() else ""
for token in [
    "+DAED_USE_VMLINUX_BTF:vmlinux-btf",
    "+vmlinux-btf",
    "define Package/daed/config",
]:
    if token not in patcher_text:
        errors.append(f"DAED patcher safeguard missing: {token}")

for old_source in [
    "VIKINGYFY/immortalwrt",
    "immortalwrt/immortalwrt.git",
]:
    if old_source in workflow:
        errors.append(f"old source reference found: {old_source}")

for path in ROOT.rglob("*"):
    if not path.is_file() or ".git" in path.parts or "__pycache__" in path.parts:
        continue
    data = path.read_bytes()
    if b"\r\n" in data:
        errors.append(f"CRLF line endings: {path.relative_to(ROOT)}")
    text = data.decode("utf-8", errors="ignore")
    if re.search(r"^(<<<<<<< |=======\s*$|>>>>>>> )", text, re.MULTILINE):
        errors.append(f"merge conflict marker: {path.relative_to(ROOT)}")

if errors:
    print("PROJECT CHECK FAILED", file=sys.stderr)
    for error in errors:
        print(f"- {error}", file=sys.stderr)
    raise SystemExit(1)

print(f"PROJECT CHECK PASSED ({len(required_files)} required files)")
