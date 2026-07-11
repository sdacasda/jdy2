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
