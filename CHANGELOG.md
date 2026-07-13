# Changelog

## v17

- One build produces initramfs and sysupgrade.
- Preserves the v16-proven RAM emergency network.
- Includes DAED, detached BTF and Athena display together.
- Pins openwrt-daede to v2026.07.09.
- Disables DAED and display services by default.
- Removes the overlapping QCN9074 DD-WRT firmware selection.
- Preserves the exact working LiBwrt source commit and 6 MiB HLOS limit.

## v18

- Adds `luci-app-wol`, `etherwake` and Simplified Chinese WOL translation.
- Adds build-time checks that all WOL packages survive `make defconfig`.
- Adds `etherwake` to the full-feature RAM diagnostic check.
- Keeps the same pinned LiBwrt/DAED/BTF/display baseline and one-build workflow.
