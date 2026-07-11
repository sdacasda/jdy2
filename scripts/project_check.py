#!/usr/bin/env python3
from __future__ import annotations

import json
import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]

REQUIRED_FILES = {
    ".gitattributes",
    ".github/workflows/build-athena-daed.yml",
    ".github/workflows/validate-project.yml",
    "config/athena-daed.config",
    "scripts/project_check.py",
    "scripts/prepare_packages.sh",
    "scripts/apply_defaults.sh",
    "scripts/verify_config.sh",
    "scripts/collect_output.sh",
    "scripts/verify_after_flash.sh",
    "README.md",
    "PROJECT.json",
    "AUDIT.md",
    "docs/BUILD.md",
    "docs/FLASH.md",
    "docs/UPDATE.md",
}

FORBIDDEN_PATHS = {
    "config/athena-dae.config",
    "scripts/check-build-config.sh",
    "刷机与DAED验收说明.md",
}

TEXT_SUFFIXES = {".sh", ".py", ".yml", ".yaml", ".md", ".config", ".json", ".txt", ""}

REQUIRED_CONFIG = {
    "CONFIG_TARGET_qualcommax=y",
    "CONFIG_TARGET_qualcommax_ipq60xx=y",
    "CONFIG_BPF_TOOLCHAIN_HOST=y",
    "CONFIG_USE_LLVM_HOST=y",
    "CONFIG_DWARVES=y",
    "CONFIG_KERNEL_DEBUG_INFO_BTF=y",
    "CONFIG_KERNEL_DEBUG_INFO_BTF_MODULES=y",
    "CONFIG_KERNEL_KPROBES=y",
    "CONFIG_KERNEL_KPROBE_EVENTS=y",
    "CONFIG_KERNEL_XDP_SOCKETS=y",
    "CONFIG_PACKAGE_kmod-sched-core=y",
    "CONFIG_PACKAGE_kmod-sched-bpf=y",
    "CONFIG_PACKAGE_kmod-veth=y",
    "CONFIG_PACKAGE_daed=y",
    "CONFIG_DAED_USE_KERNEL_BTF=y",
    "CONFIG_PACKAGE_luci-app-daede=y",
    "CONFIG_PACKAGE_luci-app-daede_daed=y",
}

FORBIDDEN_ENABLED_CONFIG = {
    "CONFIG_PACKAGE_dae=y",
    "CONFIG_PACKAGE_luci-app-daede_dae=y",
    "CONFIG_PACKAGE_luci-app-passwall=y",
    "CONFIG_PACKAGE_luci-app-passwall2=y",
    "CONFIG_PACKAGE_luci-app-openclash=y",
    "CONFIG_PACKAGE_luci-app-homeproxy=y",
    "CONFIG_PACKAGE_kmod-qca-nss-ecm=y",
}

errors: list[str] = []

for rel in sorted(REQUIRED_FILES):
    if not (ROOT / rel).is_file():
        errors.append(f"missing required file: {rel}")

for rel in sorted(FORBIDDEN_PATHS):
    if (ROOT / rel).exists():
        errors.append(f"stale/forbidden file still present: {rel}")

for path in ROOT.rglob("*"):
    if not path.is_file() or ".git" in path.parts or "__pycache__" in path.parts:
        continue
    if path.suffix.lower() not in TEXT_SUFFIXES and path.name not in {
        ".gitattributes", ".gitignore", "LICENSE"
    }:
        continue

    data = path.read_bytes()
    rel = path.relative_to(ROOT).as_posix()

    if b"\r\n" in data:
        errors.append(f"CRLF line endings found: {rel}")

    text = data.decode("utf-8", errors="replace")
    if re.search(r"^(<<<<<<< |=======\s*$|>>>>>>> )", text, flags=re.MULTILINE):
        errors.append(f"unresolved merge-conflict marker: {rel}")

try:
    meta = json.loads((ROOT / "PROJECT.json").read_text(encoding="utf-8"))
    if meta.get("backend") != "daed":
        errors.append("PROJECT.json backend must be daed")
    if meta.get("device") != "JDCloud RE-CS-02":
        errors.append("PROJECT.json device mismatch")
except Exception as exc:
    errors.append(f"PROJECT.json is invalid: {exc}")

cfg_path = ROOT / "config/athena-daed.config"
if cfg_path.is_file():
    cfg_lines = {
        line.strip()
        for line in cfg_path.read_text(encoding="utf-8").splitlines()
        if line.strip() and not line.lstrip().startswith("#")
    }
    for item in sorted(REQUIRED_CONFIG):
        if item not in cfg_lines:
            errors.append(f"required config missing: {item}")
    for item in sorted(FORBIDDEN_ENABLED_CONFIG):
        if item in cfg_lines:
            errors.append(f"conflicting config enabled: {item}")

workflow = ROOT / ".github/workflows/build-athena-daed.yml"
if workflow.is_file():
    workflow_text = workflow.read_text(encoding="utf-8")
    for token in [
        "VIKINGYFY/immortalwrt",
        "kenzok8/openwrt-daede",
        "actions/upload-artifact@v4",
        "scripts/project_check.py",
        "scripts/verify_config.sh",
        "bash scripts/collect_output.sh",
        "bash scripts/prepare_packages.sh",
        "if-no-files-found: warn",
        "Existing runner swap detected; no new swap file is needed.",
        "$RUNNER_TEMP/athena-build.swap",
        "Install build dependencies without upgrading runner",
        "--no-install-recommends",
    ]:
        if token not in workflow_text:
            errors.append(f"workflow missing required token: {token}")


    for forbidden_token in [
        "init_build_environment.sh",
        "apt full-upgrade",
        "apt-get full-upgrade",
        "build-scripts.immortalwrt.org",
    ]:
        if forbidden_token in workflow_text:
            errors.append(f"destructive/external runner initializer found: {forbidden_token}")

prepare_script = ROOT / "scripts/prepare_packages.sh"
if prepare_script.is_file():
    prepare_text = prepare_script.read_text(encoding="utf-8")
    for token in [
        "package/feeds/luci/luci-app-dae",
        "package/feeds/luci/luci-app-daed",
        "DAED_USE_VMLINUX_BTF:vmlinux-btf",
        "DEPENDS:=+luci-base +daed",
    ]:
        if token not in prepare_text:
            errors.append(f"prepare_packages.sh missing required DAED-only patch token: {token}")

defaults_script = ROOT / "scripts/apply_defaults.sh"
if defaults_script.is_file():
    defaults_text = defaults_script.read_text(encoding="utf-8")
    for token in [
        "flow_offloading='0'",
        "flow_offloading_hw='0'",
    ]:
        if token not in defaults_text:
            errors.append(f"apply_defaults.sh missing runtime offload safeguard: {token}")

if errors:
    print("PROJECT CHECK FAILED", file=sys.stderr)
    for error in errors:
        print(f" - {error}", file=sys.stderr)
    raise SystemExit(1)

print("PROJECT CHECK PASSED")
print(f"Checked {sum(1 for p in ROOT.rglob('*') if p.is_file() and '__pycache__' not in p.parts)} files.")
