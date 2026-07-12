#!/usr/bin/env bash
set -euo pipefail

TOPDIR="${1:?usage: apply_defaults.sh OPENWRT_TOPDIR}"
TOPDIR="$(cd "$TOPDIR" && pwd)"

DEFAULTS_DIR="$TOPDIR/package/base-files/files/etc/uci-defaults"
mkdir -p "$DEFAULTS_DIR"

cat > "$DEFAULTS_DIR/99-athena-minimal-daed" <<'EOF'
#!/bin/sh

uci -q batch <<'UCI'
set system.@system[0].hostname='Athena-DAED'
set network.lan.ipaddr='192.168.1.1'
set firewall.@defaults[0].flow_offloading='0'
set firewall.@defaults[0].flow_offloading_hw='0'
set athena_led.config.enable='1'
set daed.config.enabled='0'
set daede.config.enabled='0'
commit system
commit network
commit firewall
commit athena_led
commit daed
commit daede
UCI

# DAED must see traffic before acceleration paths. Keep NSS device drivers,
# but disable optional forwarding accelerators when their init scripts exist.
for svc in qca-nss-ecm ecm shortcut-fe sfe; do
    if [ -x "/etc/init.d/$svc" ]; then
        "/etc/init.d/$svc" disable >/dev/null 2>&1 || true
        "/etc/init.d/$svc" stop >/dev/null 2>&1 || true
    fi
done

exit 0
EOF
chmod +x "$DEFAULTS_DIR/99-athena-minimal-daed"

cat > "$TOPDIR/package/base-files/files/etc/banner" <<'EOF'
  ___  _   _                      ____    _    _____ ____  
 / _ \| |_| |__   ___ _ __   __ _|  _ \  / \  | ____|  _ \ 
| | | | __| '_ \ / _ \ '_ \ / _` | | | |/ _ \ |  _| | | | |
| |_| | |_| | | |  __/ | | | (_| | |_| / ___ \| |___| |_| |
 \___/ \__|_| |_|\___|_| |_|\__,_|____/_/   \_\_____|____/ 

 Athena AX6600 minimal LiBwrt build: DAED + front display
EOF
