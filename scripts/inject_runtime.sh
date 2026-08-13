#!/usr/bin/env bash
set -euo pipefail
TOPDIR="${1:?usage: inject_runtime.sh OPENWRT_TOPDIR}"
FILES="$TOPDIR/package/base-files/files"
mkdir -p "$FILES/etc/uci-defaults" "$FILES/etc" "$FILES/www"

cp "$(dirname "$0")/../PROJECT.json" "$FILES/etc/athena-project.json"
cat >"$FILES/etc/athena-release" <<'EOF'
ATHENA_VERSION='19.0.0-rc2'
ATHENA_LAN='192.168.50.1'
ATHENA_PROFILE='stable'
EOF

cat >"$FILES/etc/uci-defaults/99-athena-v19-safe-defaults" <<'EOF'
#!/bin/sh
uci -q batch <<'UCI'
set system.@system[0].hostname='Athena-AX6600'
set network.lan.ipaddr='192.168.50.1'
set network.lan.netmask='255.255.255.0'
set firewall.@defaults[0].flow_offloading='0'
set firewall.@defaults[0].flow_offloading_hw='0'
set daed.config.enabled='0'
set daed.config.listen_addr='127.0.0.1:2023'
set athena.main.enabled='0'
set athena.main.iot_enabled='0'
commit system
commit network
commit firewall
commit daed
commit athena
UCI
/etc/init.d/daed disable >/dev/null 2>&1 || true
/etc/init.d/daed stop >/dev/null 2>&1 || true
/etc/init.d/athena_led disable >/dev/null 2>&1 || true
/etc/init.d/athena_led stop >/dev/null 2>&1 || true
exit 0
EOF
chmod +x "$FILES/etc/uci-defaults/99-athena-v19-safe-defaults"

cat >"$FILES/www/diag.html" <<'EOF'
<!doctype html><meta charset="utf-8"><title>Athena v19 Recovery</title>
<h1>Athena AX6600 v19</h1>
<p>Normal LuCI: <a href="http://192.168.50.1/">192.168.50.1</a></p>
<p>Recovery LuCI: <a href="http://192.168.50.1:8080/">192.168.50.1:8080</a></p>
<p>DAED is disabled by default. Add subscriptions and nodes in LuCI through Services &rarr; Athena &rarr; DAED Panel.</p>
<p>Optional IoT network: <code>athena-iot setup</code>.</p>
EOF
