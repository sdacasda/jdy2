#!/usr/bin/env bash
set -euo pipefail

OPENWRT_DIR="${1:?openwrt source directory is required}"
LAN_IP="${LAN_IP:-192.168.50.1}"
HOSTNAME="${HOSTNAME:-Athena-DAED}"

DEFAULTS_DIR="$OPENWRT_DIR/package/base-files/files/etc/uci-defaults"
mkdir -p "$DEFAULTS_DIR"

cat > "$DEFAULTS_DIR/99-athena-daed-defaults" <<EOF
#!/bin/sh
uci set network.lan.ipaddr='$LAN_IP'
uci set system.@system[0].hostname='$HOSTNAME'
uci commit network
uci commit system
exit 0
EOF

chmod +x "$DEFAULTS_DIR/99-athena-daed-defaults"
