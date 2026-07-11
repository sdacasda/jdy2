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

# kmod-nft-offload is a target-default package in this source tree.
# Keep both software and hardware flow offload disabled so traffic is not
# fast-pathed around DAED's eBPF hooks.
if uci -q get firewall.@defaults[0] >/dev/null 2>&1; then
    uci set firewall.@defaults[0].flow_offloading='0'
    uci set firewall.@defaults[0].flow_offloading_hw='0'
fi

uci commit network
uci commit system
uci commit firewall
exit 0
EOF

chmod +x "$DEFAULTS_DIR/99-athena-daed-defaults"
