# GitHub Actions run 10 fix

## Primary failure

Run 10 did not fail in Artifact collection. The first fatal build error was:

```text
bash: line 1: /invalid/clang: No such file or directory
include/bpf.mk:82: ERROR: LLVM/clang version too old
ERROR: package/kernel/bpf-headers failed to build
```

The later `Expected one initramfs, found 0` message was a consequence of the
compile failure.

## Root cause

The locked source-built DAED package depends on `bpf-headers` and includes
OpenWrt's `bpf.mk`, but its package dependency list did not include
`$(BPF_DEPENDS)`. LiBwrt therefore knew that BPF support existed without
selecting an actual LLVM backend. In that unresolved state `bpf.mk` deliberately
uses `/invalid/clang`.

## Fix

- Patch the imported DAED package to add `$(BPF_DEPENDS)`.
- Select OpenWrt's host BPF toolchain in `config/athena-v19.config`.
- Install the complete host LLVM toolset in GitHub Actions.
- Verify `clang`, `llc`, `llvm-dis`, `opt`, and `llvm-strip` before cloning and
  building OpenWrt.
- Reject an effective OpenWrt config that has no resolved LLVM backend.
- Add regression tests for the DAED transformation, config guard, and workflow
  dependency contract.

## Expected run 11 behavior

The effective config must include:

```text
CONFIG_BPF_TOOLCHAIN_HOST=y
CONFIG_USE_LLVM_HOST=y
```

The `Verify effective OpenWrt config` step will now stop immediately if no
usable LLVM backend was selected. A successful cloud build must still pass the
compile, DAED provenance, firmware inspection, Artifact collection, and final
result gates.

