# Build guide

Use `build_mode=validate` first. It checks:

- repository consistency;
- RE-CS-02 support in upstream source;
- unresolved conflict markers;
- feeds and DAED package availability;
- `make defconfig`;
- device, BTF, eBPF and DAED selections;
- host LLVM eBPF output.

Use `build_mode=build` only after validation succeeds.

A successful artifact must contain an RE-CS-02 sysupgrade image, manifest,
`BUILD_INFO.txt`, `SHA256SUMS`, final `.config` and the post-flash verifier.
Artifacts from failed runs are diagnostic only.
## Kernel image limit

The RE-CS-02 uImage must not exceed 6,291,456 bytes. Detached BTF is used to
meet this fixed limit. Never patch the profile to `KERNEL_SIZE := 8192k`.

## DWARVES/pahole in detached-BTF mode

`CONFIG_DWARVES` is an OpenWrt host-tool selector normally retained when the
main kernel enables debug BTF. In this project the main kernel debug/BTF options
are intentionally disabled, so `make defconfig` may remove that symbol. The
workflow installs and verifies the host `pahole` binary used by the detached
`vmlinux-btf` package instead.

## v12 kernel trim

The boot kernel intentionally excludes tracing/profiling facilities that DAED
does not require: BPF events, ftrace, kprobes and perf events. Networking eBPF,
TC BPF, cgroup BPF, XDP sockets and detached BTF remain enabled.

