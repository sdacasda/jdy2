# Build notes

## Pinned baseline

- Repository: `https://github.com/LiBwrt/openwrt-6.x.git`
- Branch lineage: `main-nss`
- Exact commit: `cf9444c1b20458687898489b36e1aebf56d9baf2`
- Target: `qualcommax/ipq60xx`
- Device: `jdcloud_re-cs-02`
- Kernel line: `6.12`
- Physical HLOS size: `6,291,456` bytes

The exact commit is used instead of following the moving branch.

## Package inputs

The workflow records the actual commits used for:

- `kenzok8/openwrt-daede`
- `kenzok8/vmlinux-btf`
- `NONGFAH/luci-app-athena-led`
- `sbwml/packages_lang_golang` branch `26.x`

These package repositories move independently, so their resolved commits are written into `BUILD_INFO.txt`.

## Why detached BTF

DAED uses CO-RE eBPF and needs matching kernel BTF. The boot kernel has a fixed 6 MiB HLOS slot. `vmlinux-btf` builds matching BTF from the same source/config and installs it under `/usr/lib/debug/boot/`, avoiding integrated debug BTF in the persistent boot image.

## Why NSS remains but acceleration is disabled

The known-good LiBwrt source uses NSS device drivers. Removing that baseline would increase boot risk. The first-boot defaults retain the drivers but disable optional ECM/SFE forwarding services and LuCI flow-offload flags so DAED can see traffic.
