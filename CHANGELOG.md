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
