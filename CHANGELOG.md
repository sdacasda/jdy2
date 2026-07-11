# Changelog

## v2

- Normalize shell-script line endings and permissions inside GitHub Actions.
- Invoke repository shell scripts explicitly through `bash`.
- Always create `output/WORKFLOW_STATUS.txt` before diagnostics collection.
- Do not require a firmware image in `build_mode=validate`.
- Do not add a second red error when no artifact files exist.

## v3

- Fix ShellCheck SC2164 in `collect_output.sh`.
- Validation workflow now passes ShellCheck instead of exiting with code 1.

## v4

- Reuses the swap already supplied by GitHub's Ubuntu runner.
- Never rewrites an active `/swapfile`.
- Creates an isolated fallback swap under `$RUNNER_TEMP` only when no swap exists.
- Falls back from `fallocate` to `dd`.
- Treats optional swap creation failure as a warning rather than a build failure.

## v5

- Removes the external ImmortalWrt environment initializer.
- Avoids whole-runner operating-system upgrades and APT-source rewrites.
- Does not replace GitHub runner Node.js, Go, GCC or LLVM binaries.
- Installs only the documented build dependencies with APT.
- Prints tool versions before cloning and building.
- Adds a project check preventing the external initializer from returning.

## v6

- Stops treating target-default `kmod-nft-offload` as a configuration conflict.
- Explicitly disables software and hardware flow offload at first boot.
- Removes unused legacy LuCI dae/daed feed packages from the build tree.
- Makes `luci-app-daede` depend directly on `daed`.
- Removes the unused optional `vmlinux-btf` package dependency.
- Keeps integrated kernel BTF as the only supported BTF mode.

## v7

- Fixes ShellCheck SC2251 in `prepare_packages.sh`.
- Replaces the standalone `! grep` assertion with an explicit `if` block.
- Uses a Bash array for stale feed-package checks.
- Makes CI fail only on ShellCheck warning/error severity, not info-only hints.
- Adds targeted regression checks without misclassifying multiline conditions.

## v8

- Removes the custom `package/kernel/bpf-headers/compile` prebuild.
- Restores the standard OpenWrt `world` dependency order.
- Makes the full build target explicit as `make ... world`.
- Prevents package compilation before host tools, toolchain and target state exist.
- Stops deleting the unrelated `package/feeds/video/sdl3` package.
- Adds project checks preventing both regressions.
## v9

- Fixes RE-CS-02 `uImage.itb is too big` without enlarging the 6144 KiB kernel slot.
- Disables main-kernel DWARF, integrated BTF and module BTF.
- Adds `kenzok8/vmlinux-btf` as detached BTF in the root filesystem.
- Selects `DAED_USE_VMLINUX_BTF` and keeps DAED's upstream dependency.
- Records actual uImage size and the fixed device limit in diagnostics.
- Updates post-flash checks to accept detached BTF.
- Rejects unsafe attempts to change RE-CS-02 `KERNEL_SIZE` to 8192 KiB.

