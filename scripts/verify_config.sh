#!/bin/sh
set -eu
CONFIG="${1:?usage: verify_config.sh CONFIG [DAED_MAKEFILE]}"
for token in \
 CONFIG_TARGET_qualcommax=y \
 CONFIG_TARGET_qualcommax_ipq60xx=y \
 CONFIG_TARGET_qualcommax_ipq60xx_DEVICE_jdcloud_re-cs-02=y \
 CONFIG_TARGET_ROOTFS_INITRAMFS=y \
 CONFIG_TARGET_ROOTFS_SQUASHFS=y \
 CONFIG_PACKAGE_daed=y \
 CONFIG_PACKAGE_luci-app-daede=y \
 CONFIG_PACKAGE_athena-runtime=y \
 CONFIG_PACKAGE_luci-app-athena=y \
 CONFIG_PACKAGE_luci-theme-argon=y \
 CONFIG_PACKAGE_luci-app-argon-config=y \
 CONFIG_PACKAGE_nginx=y \
 CONFIG_PACKAGE_uhttpd=y \
 CONFIG_PACKAGE_ath11k-firmware-qcn9074=y
do
	grep -Fxq "$token" "$CONFIG" || { echo "FAIL missing:$token" >&2; exit 1; }
done
for forbidden in smartdns luci-app-smartdns luci-app-openclash luci-app-passwall luci-app-homeproxy ath11k-firmware-qcn9074-ddwrt; do
	! grep -Fxq "CONFIG_PACKAGE_${forbidden}=y" "$CONFIG" || { echo "FAIL forbidden:$forbidden" >&2; exit 1; }
done
echo "PASS: v19 config"
