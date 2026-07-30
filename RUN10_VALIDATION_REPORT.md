# Run 10 repair validation report

Date: 2026-07-30

## Evidence inspected

- Run outcome summary: compile failed, DAED post-build verification skipped,
  firmware inspection failed.
- Full build log: first fatal package failure was `bpf-headers`.
- Effective OpenWrt config: `CONFIG_HAS_BPF_TOOLCHAIN=y` was present while no
  `CONFIG_USE_LLVM_HOST`, `CONFIG_USE_LLVM_PREBUILT`, or
  `CONFIG_USE_LLVM_BUILD` backend was selected.
- Locked LiBwrt `include/bpf.mk` and `toolchain/Config.in`.
- Locked DAED package Makefile.

## Test-driven repair

The following regression checks were added and observed failing before the
production change:

1. Imported DAED must select `$(BPF_DEPENDS)`.
2. Effective config verification must reject an unresolved BPF toolchain.
3. GitHub Actions must install and verify the complete host LLVM toolset.

All three passed after the minimal repair.

## Local verification

```text
Python unit/behavior tests: 48/48 passed
OpenWrt runtime shell tests: 8/8 passed
Dashboard chart test: passed
Project structure validation: passed
DAED template validation: passed
Package layout validation: passed
Web configuration validation: passed
Sensitive-information scan: passed
Locked upstream DAED Makefile transformation: passed
```

The real locked DAED Makefile was transformed to contain:

```make
DEPENDS:=$(BPF_DEPENDS) $(GO_ARCH_DEPENDS) \
    ...
    +vmlinux-btf
```

## Remaining gate

A complete Linux/OpenWrt compilation cannot be reproduced in the Windows
desktop workspace. GitHub Actions run 11 remains required to prove:

- OpenWrt `defconfig` resolves `CONFIG_USE_LLVM_HOST=y`;
- DAED and its eBPF objects compile with the installed host LLVM toolset;
- exactly one initramfs and one sysupgrade image are generated;
- firmware inspection and Artifact checksum validation pass.

Do not flash sysupgrade until the new initramfs has passed real-device testing.

