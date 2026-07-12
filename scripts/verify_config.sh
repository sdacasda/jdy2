#!/usr/bin/env bash
set -euo pipefail

CONFIG_FILE="${1:-.config}"
[[ -f "$CONFIG_FILE" ]] || {
    echo "::error::Config file not found: $CONFIG_FILE"
    exit 1
}

required=(
    "CONFIG_TARGET_qualcommax=y"
    "CONFIG_TARGET_qualcommax_ipq60xx=y"
    "CONFIG_TARGET_qualcommax_ipq60xx_DEVICE_jdcloud_re-cs-02=y"
    "CONFIG_TARGET_ROOTFS_SQUASHFS=y"
    "CONFIG_TARGET_ROOTFS_INITRAMFS=y"
    "CONFIG_NSS_FIRMWARE_VERSION_11_4=y"
    "CONFIG_PACKAGE_daed=y"
    "CONFIG_PACKAGE_luci-app-daede=y"
    "CONFIG_PACKAGE_luci-app-daede_daed=y"
    "CONFIG_PACKAGE_kmod-sched-core=y"
    "CONFIG_PACKAGE_kmod-sched-bpf=y"
    "CONFIG_PACKAGE_kmod-veth=y"
    "CONFIG_KERNEL_XDP_SOCKETS=y"
    "CONFIG_DAED_USE_VMLINUX_BTF=y"
    "CONFIG_PACKAGE_vmlinux-btf=y"
    "CONFIG_PACKAGE_luci-app-athena-led=y"
)

for setting in "${required[@]}"; do
    if ! grep -Fxq "$setting" "$CONFIG_FILE"; then
        echo "::error::Required setting was removed by make defconfig: $setting"
        exit 1
    fi
done

for forbidden in \
    "CONFIG_KERNEL_DEBUG_INFO_BTF=y" \
    "CONFIG_DAED_USE_KERNEL_BTF=y" \
    "CONFIG_PACKAGE_luci-app-openclash=y" \
    "CONFIG_PACKAGE_luci-app-passwall=y" \
    "CONFIG_PACKAGE_luci-app-homeproxy=y" \
    "CONFIG_PACKAGE_luci-app-dockerman=y" \
    "CONFIG_PACKAGE_luci-app-samba4=y" \
    "CONFIG_PACKAGE_luci-app-adguardhome=y"; do
    if grep -Fxq "$forbidden" "$CONFIG_FILE"; then
        echo "::error::Forbidden setting is enabled: $forbidden"
        exit 1
    fi
done

echo "Effective configuration is valid."
grep -E \
    'TARGET_qualcommax|jdcloud_re-cs-02|ROOTFS_INITRAMFS|PACKAGE_(daed|luci-app-daede|vmlinux-btf|luci-app-athena-led|kmod-sched-bpf)|KERNEL_XDP_SOCKETS|DAED_USE_' \
    "$CONFIG_FILE" || true
