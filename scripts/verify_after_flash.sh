#!/bin/sh
set -u

fail=0

ok() {
    printf '[OK] %s\n' "$1"
}

bad() {
    printf '[FAIL] %s\n' "$1"
    fail=1
}

board="$(ubus call system board 2>/dev/null)"
echo "$board" | grep -q '"board_name": "jdcloud,re-cs-02"' \
    && ok "board is jdcloud,re-cs-02" \
    || bad "unexpected board"

case "$(uname -r)" in
    6.12.*) ok "kernel is on the pinned 6.12 line: $(uname -r)" ;;
    *) bad "unexpected kernel: $(uname -r)" ;;
esac

for pkg in daed luci-app-daede vmlinux-btf luci-app-athena-led kmod-sched-bpf kmod-veth; do
    opkg status "$pkg" 2>/dev/null | grep -q 'Status: install ok installed' \
        && ok "package installed: $pkg" \
        || bad "package missing: $pkg"
done

if [ -r /sys/kernel/btf/vmlinux ]; then
    ok "integrated kernel BTF is available"
elif [ -r /usr/lib/debug/boot/vmlinux ]; then
    ok "detached BTF is available"
else
    bad "no integrated or detached BTF found"
fi

for module in cls_bpf act_bpf veth; do
    modprobe "$module" >/dev/null 2>&1 \
        && ok "kernel module loads: $module" \
        || bad "kernel module failed: $module"
done

[ -x /usr/sbin/athena-led ] \
    && ok "Athena display binary is executable" \
    || bad "Athena display binary is missing"

[ -x /etc/init.d/athena_led ] \
    && ok "Athena display service exists" \
    || bad "Athena display service is missing"

if [ -e /dev/mmcblk0p16 ]; then
    hlos_bytes="$(blockdev --getsize64 /dev/mmcblk0p16 2>/dev/null || echo unknown)"
    [ "$hlos_bytes" = "6291456" ] \
        && ok "HLOS remains 6 MiB" \
        || bad "unexpected HLOS size: $hlos_bytes"
fi

if [ -r /dev/mmcblk0p2 ]; then
    boot_slot="$(hexdump -e '1/1 "%u\n"' -n 1 -s 148 /dev/mmcblk0p2 2>/dev/null || echo unknown)"
    printf '[INFO] BOOTCONFIG slot byte: %s\n' "$boot_slot"
fi

printf '\nDAED is intentionally disabled by default. Configure it in LuCI first.\n'
exit "$fail"
