# Changelog

## v13

- Rebuilt from scratch on the exact LiBwrt commit used by the known-good 6.12.94 firmware.
- Targets only JDCloud RE-CS-02.
- Adds DAED with the daed LuCI backend.
- Adds matching detached BTF.
- Adds the Athena front-display LuCI package.
- Preserves the stable NSS/device baseline without aggressive kernel trimming.
- Generates an initramfs RAM-test image before persistent sysupgrade.
- Enforces the physical 6 MiB HLOS limit.
- Removes unrelated large application selections.

## v14

- Fixes LiBwrt `make defconfig` removing `CONFIG_DAED_USE_VMLINUX_BTF`.
- Patches the copied DAED Makefile to depend on `vmlinux-btf` unconditionally.
- Removes the optional `DAED_USE_KERNEL_BTF` / `DAED_USE_VMLINUX_BTF` choice
  from the copied package definition.
- Keeps `CONFIG_PACKAGE_vmlinux-btf=y` and integrated kernel BTF disabled.
- Verifies the patched DAED dependency before compilation.

