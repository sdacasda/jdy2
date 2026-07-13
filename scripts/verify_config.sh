#!/usr/bin/env bash
set -euo pipefail

CONFIG_FILE="${1:-.config}"
DAED_MAKEFILE="${2:-package/custom/daed/Makefile}"
[[ -f "$CONFIG_FILE" ]] || { echo "::error::Config file not found: $CONFIG_FILE"; exit 1; }

required=(
  "CONFIG_TARGET_qualcommax=y"
  "CONFIG_TARGET_qualcommax_ipq60xx=y"
  "CONFIG_TARGET_qualcommax_ipq60xx_DEVICE_jdcloud_re-cs-02=y"
  "CONFIG_TARGET_ROOTFS_SQUASHFS=y"
  "CONFIG_TARGET_ROOTFS_INITRAMFS=y"
  "CONFIG_NSS_FIRMWARE_VERSION_11_4=y"
  "CONFIG_PACKAGE_ath11k-firmware-qcn9074=y"
  "CONFIG_PACKAGE_daed=y"
  "CONFIG_PACKAGE_luci-app-daede=y"
  "CONFIG_PACKAGE_luci-app-daede_daed=y"
  "CONFIG_PACKAGE_kmod-sched-core=y"
  "CONFIG_PACKAGE_kmod-sched-bpf=y"
  "CONFIG_PACKAGE_kmod-veth=y"
  "CONFIG_KERNEL_XDP_SOCKETS=y"
  "CONFIG_PACKAGE_vmlinux-btf=y"
  "CONFIG_PACKAGE_luci-app-athena-led=y"
  "CONFIG_PACKAGE_dropbear=y"
  "CONFIG_PACKAGE_uhttpd=y"
  "CONFIG_PACKAGE_luci-app-wol=y"
  "CONFIG_PACKAGE_luci-i18n-wol-zh-cn=y"
  "CONFIG_PACKAGE_etherwake=y"
)
for setting in "${required[@]}"; do
  grep -Fxq "$setting" "$CONFIG_FILE" || { echo "::error::Required setting removed by defconfig: $setting"; exit 1; }
done

for forbidden in \
  "CONFIG_PACKAGE_ath11k-firmware-qcn9074-ddwrt=y" \
  "CONFIG_KERNEL_DEBUG_INFO_BTF=y" \
  "CONFIG_DAED_USE_KERNEL_BTF=y" \
  "CONFIG_DAED_USE_VMLINUX_BTF=y" \
  "CONFIG_PACKAGE_luci-app-openclash=y" \
  "CONFIG_PACKAGE_luci-app-passwall=y" \
  "CONFIG_PACKAGE_luci-app-homeproxy=y" \
  "CONFIG_PACKAGE_luci-app-dockerman=y" \
  "CONFIG_PACKAGE_luci-app-samba4=y"; do
  if grep -Fxq "$forbidden" "$CONFIG_FILE"; then
    echo "::error::Forbidden setting enabled: $forbidden"
    exit 1
  fi
done

[[ -f "$DAED_MAKEFILE" ]] || { echo "::error::Patched DAED Makefile missing"; exit 1; }
grep -Fq '+vmlinux-btf' "$DAED_MAKEFILE" || { echo "::error::DAED lacks direct vmlinux-btf dependency"; exit 1; }
if grep -q 'DAED_USE_' "$DAED_MAKEFILE"; then
  echo "::error::Unsupported DAED_USE_* choice symbols remain"
  exit 1
fi

echo "Final-candidate configuration is valid."
