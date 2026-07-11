#!/usr/bin/env bash
set -euo pipefail

CONFIG_FILE="${1:-.config}"

required=(
    "CONFIG_TARGET_qualcommax=y"
    "CONFIG_TARGET_qualcommax_ipq60xx=y"
    "CONFIG_BPF_TOOLCHAIN_HOST=y"
    "CONFIG_USE_LLVM_HOST=y"
    "CONFIG_DWARVES=y"
    "CONFIG_KERNEL_DEBUG_INFO_BTF=y"
    "CONFIG_KERNEL_DEBUG_INFO_BTF_MODULES=y"
    "CONFIG_KERNEL_KPROBES=y"
    "CONFIG_KERNEL_KPROBE_EVENTS=y"
    "CONFIG_KERNEL_XDP_SOCKETS=y"
    "CONFIG_PACKAGE_kmod-sched-core=y"
    "CONFIG_PACKAGE_kmod-sched-bpf=y"
    "CONFIG_PACKAGE_kmod-veth=y"
    "CONFIG_PACKAGE_daed=y"
    "CONFIG_DAED_USE_KERNEL_BTF=y"
    "CONFIG_PACKAGE_luci-app-daede=y"
    "CONFIG_PACKAGE_luci-app-daede_daed=y"
)

for item in "${required[@]}"; do
    grep -qxF "$item" "$CONFIG_FILE" || {
        echo "::error::Required setting was removed by make defconfig: $item"
        exit 1
    }
done

if ! grep -qE '^CONFIG_TARGET(_DEVICE)?_qualcommax_ipq60xx_DEVICE_jdcloud_re-cs-02=y$' "$CONFIG_FILE"; then
    echo "::error::JDCloud RE-CS-02 device profile is not selected."
    exit 1
fi

for forbidden in \
    "CONFIG_PACKAGE_dae=y" \
    "CONFIG_PACKAGE_luci-app-daede_dae=y" \
    "CONFIG_PACKAGE_luci-app-passwall=y" \
    "CONFIG_PACKAGE_luci-app-passwall2=y" \
    "CONFIG_PACKAGE_luci-app-openclash=y" \
    "CONFIG_PACKAGE_luci-app-homeproxy=y" \
    "CONFIG_PACKAGE_kmod-qca-nss-ecm=y" \
    "CONFIG_PACKAGE_kmod-nft-offload=y"
do
    if grep -qxF "$forbidden" "$CONFIG_FILE"; then
        echo "::error::Conflicting setting enabled: $forbidden"
        exit 1
    fi
done

echo "Effective DAED/BTF configuration:"
grep -E \
    'CONFIG_(TARGET.*jdcloud_re-cs-02|BPF_TOOLCHAIN_HOST|USE_LLVM_HOST|DWARVES|KERNEL_DEBUG_INFO_BTF|KERNEL_KPROBES|KERNEL_XDP_SOCKETS|PACKAGE_kmod-sched-bpf|PACKAGE_kmod-veth|PACKAGE_daed|DAED_USE_KERNEL_BTF|PACKAGE_luci-app-daede)' \
    "$CONFIG_FILE"

echo "CONFIG VERIFICATION PASSED"
