#!/usr/bin/env bash
set -euo pipefail

TOPDIR="${1:?usage: inject_diagnostic.sh OPENWRT_TOPDIR}"
TOPDIR="$(cd "$TOPDIR" && pwd)"

FILES="$TOPDIR/package/base-files/files"
mkdir -p "$FILES/etc/init.d" "$FILES/www" "$FILES/usr/bin"

cat > "$FILES/etc/init.d/diag-net" <<'EOF'
#!/bin/sh /etc/rc.common
START=08
STOP=90
USE_PROCD=0

start() {
    logger -t diag-net "starting emergency diagnostic network"

    # Start every plausible wired interface. Give each interface the same
    # diagnostic address so any physical port can answer without relying on
    # board-specific bridge creation.
    for path in /sys/class/net/*; do
        dev="${path##*/}"
        case "$dev" in
            lo|br-*|bond*|ifb*|sit*|gre*|gretap*|ip6tnl*|wlan*|phy*)
                continue
                ;;
        esac

        ip link set dev "$dev" up 2>/dev/null || true
        ip addr add 192.168.1.1/24 dev "$dev" 2>/dev/null || true
        logger -t diag-net "configured $dev with 192.168.1.1/24"
    done

    # Keep standard services available even when netifd fails later.
    /etc/init.d/dropbear enable >/dev/null 2>&1 || true
    /etc/init.d/dropbear start >/dev/null 2>&1 || true
    /etc/init.d/rpcd enable >/dev/null 2>&1 || true
    /etc/init.d/rpcd start >/dev/null 2>&1 || true
    /etc/init.d/uhttpd enable >/dev/null 2>&1 || true
    /etc/init.d/uhttpd start >/dev/null 2>&1 || true
}
EOF
chmod +x "$FILES/etc/init.d/diag-net"

cat > "$FILES/www/index.html" <<'EOF'
<!doctype html>
<meta charset="utf-8">
<title>Athena RAM diagnostic</title>
<style>
body{font-family:sans-serif;max-width:760px;margin:8vh auto;padding:24px;line-height:1.6}
.ok{color:#087f23;font-weight:700}
code{background:#eee;padding:.15em .35em}
</style>
<h1>Athena AX6600 RAM diagnostic</h1>
<p class="ok">The Linux kernel and initramfs reached user space.</p>
<p>This image runs only in RAM and contains no DAED, BTF or display add-ons.</p>
<p>SSH: <code>root@192.168.1.1</code> (no password on first boot).</p>
EOF

cat > "$FILES/usr/bin/diag-report" <<'EOF'
#!/bin/sh
echo "=== board ==="
ubus call system board 2>/dev/null || true
echo "=== kernel ==="
uname -a
echo "=== cmdline ==="
cat /proc/cmdline
echo "=== links ==="
ip -br link
echo "=== addresses ==="
ip -br addr
echo "=== routes ==="
ip route
echo "=== recent kernel log ==="
dmesg | tail -n 120
EOF
chmod +x "$FILES/usr/bin/diag-report"

# Make first boot predictable.
DEFAULTS="$FILES/etc/uci-defaults"
mkdir -p "$DEFAULTS"
cat > "$DEFAULTS/99-athena-ram-diag" <<'EOF'
#!/bin/sh
uci -q batch <<'UCI'
set network.lan.ipaddr='192.168.1.1'
set network.lan.netmask='255.255.255.0'
commit network
UCI
exit 0
EOF
chmod +x "$DEFAULTS/99-athena-ram-diag"
