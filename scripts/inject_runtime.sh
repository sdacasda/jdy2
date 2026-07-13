#!/usr/bin/env bash
set -euo pipefail

TOPDIR="${1:?usage: inject_runtime.sh OPENWRT_TOPDIR}"
TOPDIR="$(cd "$TOPDIR" && pwd)"
FILES="$TOPDIR/package/base-files/files"
mkdir -p "$FILES/etc/init.d" "$FILES/etc/uci-defaults" "$FILES/usr/bin" "$FILES/www"

cat > "$FILES/etc/init.d/athena-ram-net" <<'SH'
#!/bin/sh /etc/rc.common
START=08
STOP=90
USE_PROCD=0

is_ram_boot() {
    [ ! -d /rom ] && return 0
    root_type="$(awk '$2 == "/" { print $3; exit }' /proc/mounts 2>/dev/null)"
    [ "$root_type" = "rootfs" ] || [ "$root_type" = "tmpfs" ]
}

start() {
    is_ram_boot || return 0
    logger -t athena-ram-net "starting RAM-test emergency network"

    for path in /sys/class/net/*; do
        dev="${path##*/}"
        case "$dev" in
            lo|br-*|bond*|ifb*|sit*|gre*|gretap*|ip6tnl*|wlan*|phy*) continue ;;
        esac
        ip link set dev "$dev" up 2>/dev/null || true
        ip addr add 192.168.1.1/24 dev "$dev" 2>/dev/null || true
    done

    /etc/init.d/dropbear start >/dev/null 2>&1 || true
    /etc/init.d/rpcd start >/dev/null 2>&1 || true
    /etc/init.d/uhttpd start >/dev/null 2>&1 || true
}
SH
chmod +x "$FILES/etc/init.d/athena-ram-net"

cat > "$FILES/etc/uci-defaults/99-athena-daed-candidate" <<'SH'
#!/bin/sh
uci -q batch <<'UCI'
set system.@system[0].hostname='Athena-DAED'
set network.lan.ipaddr='192.168.1.1'
set network.lan.netmask='255.255.255.0'
set firewall.@defaults[0].flow_offloading='0'
set firewall.@defaults[0].flow_offloading_hw='0'
commit system
commit network
commit firewall
UCI

for svc in qca-nss-ecm ecm shortcut-fe sfe; do
    [ -x "/etc/init.d/$svc" ] || continue
    "/etc/init.d/$svc" disable >/dev/null 2>&1 || true
    "/etc/init.d/$svc" stop >/dev/null 2>&1 || true
done

[ ! -x /etc/init.d/daed ] || /etc/init.d/daed disable >/dev/null 2>&1 || true
[ ! -x /etc/init.d/daed ] || /etc/init.d/daed stop >/dev/null 2>&1 || true
[ ! -x /etc/init.d/athena_led ] || /etc/init.d/athena_led disable >/dev/null 2>&1 || true
[ ! -x /etc/init.d/athena_led ] || /etc/init.d/athena_led stop >/dev/null 2>&1 || true
exit 0
SH
chmod +x "$FILES/etc/uci-defaults/99-athena-daed-candidate"

cat > "$FILES/usr/bin/athena-feature-check" <<'SH'
#!/bin/sh
fail=0
ok(){ printf '[OK] %s\n' "$1"; }
bad(){ printf '[FAIL] %s\n' "$1"; fail=1; }

ubus call system board 2>/dev/null || true

for pkg in daed luci-app-daede vmlinux-btf luci-app-athena-led kmod-sched-bpf kmod-veth luci-app-wol etherwake; do
    if command -v apk >/dev/null 2>&1; then
        apk info -e "$pkg" >/dev/null 2>&1 && ok "package installed: $pkg" || bad "package missing: $pkg"
    else
        opkg status "$pkg" 2>/dev/null | grep -q 'Status: install ok installed' && ok "package installed: $pkg" || bad "package missing: $pkg"
    fi
done

if [ -r /sys/kernel/btf/vmlinux ]; then
    ok "integrated BTF available"
elif [ -r /usr/lib/debug/boot/vmlinux ]; then
    ok "detached BTF available"
    ls -lh /usr/lib/debug/boot/vmlinux
else
    bad "no integrated or detached BTF"
fi

for module in cls_bpf act_bpf veth; do
    modprobe "$module" >/dev/null 2>&1 && ok "module loads: $module" || bad "module failed: $module"
done

[ -x /usr/bin/daed ] && ok "daed binary exists" || bad "daed binary missing"
[ -x /usr/sbin/athena-led ] && ok "Athena display binary exists" || bad "Athena display binary missing"
[ -x /etc/init.d/athena_led ] && ok "Athena display service exists" || bad "Athena display service missing"
[ -x /usr/bin/etherwake ] && ok "etherwake binary exists" || bad "etherwake binary missing"

echo
echo "Display test:"
echo "  uci set athena_led.config.enable='1'"
echo "  uci commit athena_led"
echo "  /etc/init.d/athena_led restart"
echo
echo "Wake-on-LAN test:"
echo "  etherwake -i br-lan AA:BB:CC:DD:EE:FF"
echo "  or use LuCI: Network -> Wake on LAN"
echo
echo "DAED and display are disabled by default."
exit "$fail"
SH
chmod +x "$FILES/usr/bin/athena-feature-check"

cat > "$FILES/www/diag.html" <<'HTML'
<!doctype html>
<meta charset="utf-8">
<title>Athena DAED candidate</title>
<style>body{font-family:sans-serif;max-width:800px;margin:7vh auto;padding:24px;line-height:1.65}.ok{color:#087f23;font-weight:700}code{background:#eee;padding:.15em .35em}</style>
<h1>Athena AX6600 DAED final candidate</h1>
<p class="ok">Linux and the initramfs reached user space.</p>
<p>This image contains DAED, detached BTF, the Athena display package and Wake-on-LAN.</p>
<p>The two feature services are disabled by default for a controlled test.</p>
<p>SSH: <code>root@192.168.1.1</code>, then run <code>athena-feature-check</code>.</p>
<p><a href="/cgi-bin/luci/">Open LuCI</a></p>
HTML
