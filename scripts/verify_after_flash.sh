#!/bin/sh

echo "===== Device ====="
ubus call system board 2>/dev/null || true
uname -a
echo

echo "===== Integrated kernel BTF ====="
if [ -r /sys/kernel/btf/vmlinux ]; then
    ls -lh /sys/kernel/btf/vmlinux
    echo "BTF_OK"
else
    echo "BTF_MISSING"
fi
echo

echo "===== Required packages ====="
opkg list-installed 2>/dev/null |
    grep -E '^(daed|luci-app-daede|kmod-sched-core|kmod-sched-bpf|kmod-veth|kmod-xdp-sockets-diag|v2ray-geo)' ||
    true
echo

echo "===== DAED ====="
if command -v daed >/dev/null 2>&1; then
    daed --version 2>/dev/null || daed version 2>/dev/null || echo "DAED_BINARY_OK"
else
    echo "DAED_BINARY_MISSING"
fi

/etc/init.d/daed status 2>/dev/null || true
echo

echo "===== Dashboard/API listeners ====="
ss -lntup 2>/dev/null | grep -E 'daed|dae-wing|:2023|:2024' || true
echo

if [ -r /sys/kernel/btf/vmlinux ] && command -v daed >/dev/null 2>&1; then
    echo "RESULT=READY_FOR_DAED_CONFIGURATION"
else
    echo "RESULT=DO_NOT_START_DAED"
fi
