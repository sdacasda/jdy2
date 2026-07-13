#!/usr/bin/env bash
set -euo pipefail

CONFIG="${1:-.config}"
[[ -f "$CONFIG" ]] || {
    echo "::error::missing config: $CONFIG"
    exit 1
}

required=(
    "CONFIG_TARGET_qualcommax=y"
    "CONFIG_TARGET_qualcommax_ipq60xx=y"
    "CONFIG_TARGET_qualcommax_ipq60xx_DEVICE_jdcloud_re-cs-02=y"
    "CONFIG_TARGET_ROOTFS_INITRAMFS=y"
    "CONFIG_NSS_FIRMWARE_VERSION_11_4=y"
    "CONFIG_PACKAGE_dropbear=y"
    "CONFIG_PACKAGE_uhttpd=y"
    "CONFIG_PACKAGE_ath11k-firmware-qcn9074=y"
)

for item in "${required[@]}"; do
    grep -Fxq "$item" "$CONFIG" || {
        echo "::error::make defconfig removed required setting: $item"
        exit 1
    }
done

for forbidden in \
    "CONFIG_PACKAGE_ath11k-firmware-qcn9074-ddwrt=y" \
    "CONFIG_PACKAGE_luci=y" \
    "CONFIG_PACKAGE_luci-base=y" \
    "CONFIG_PACKAGE_daed=y" \
    "CONFIG_PACKAGE_luci-app-daede=y" \
    "CONFIG_PACKAGE_vmlinux-btf=y" \
    "CONFIG_PACKAGE_luci-app-athena-led=y" \
    "CONFIG_KERNEL_DEBUG_INFO_BTF=y"; do
    if grep -Fxq "$forbidden" "$CONFIG"; then
        echo "::error::diagnostic image unexpectedly enables: $forbidden"
        exit 1
    fi
done

echo "RAM diagnostic configuration is valid."
