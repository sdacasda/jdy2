#!/bin/sh
fail=0
check(){ if eval "$2" >/dev/null 2>&1; then echo "[PASS] $1"; else echo "[$3] $1"; [ "$3" != FAIL ] || fail=1; fi; }
check "LAN is 192.168.50.1" "[ \"$(uci -q get network.lan.ipaddr)\" = 192.168.50.1 ]" FAIL
check "DAED is loopback-only" "[ \"$(uci -q get daed.config.listen_addr)\" = 127.0.0.1:2023 ]" FAIL
check "Athena commands installed" "command -v athena-setup && command -v athena-health && command -v athena-iot" FAIL
check "Argon installed" "test -d /www/luci-static/argon" FAIL
check "Recovery listener configured" "uci show uhttpd | grep -q 192.168.50.1:8080" WARN
check "BTF available" "test -r /sys/kernel/btf/vmlinux || test -r /usr/lib/debug/boot/vmlinux" FAIL
check "Three wireless PHYs" "[ \"$(find /sys/class/ieee80211 -mindepth 1 -maxdepth 1 2>/dev/null | wc -l)\" -ge 3 ]" WARN
athena-health --verbose || fail=1
exit "$fail"
