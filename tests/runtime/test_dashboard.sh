#!/bin/sh
set -eu

fail() {
	printf 'FAIL: %s\n' "$*" >&2
	exit 1
}

ROOT="$(mktemp -d)"
trap 'rm -rf "$ROOT"' EXIT
MOCK_BIN="$ROOT/mock-bin"
mkdir -p \
	"$MOCK_BIN" \
	"$ROOT/proc" \
	"$ROOT/etc" \
	"$ROOT/sys/class/net/eth1/statistics" \
	"$ROOT/sys/class/thermal/thermal_zone0" \
	"$ROOT/sys/class/thermal/thermal_zone1" \
	"$ROOT/sys/kernel/debug/ecm" \
	"$ROOT/var/log/daed"

cat >"$ROOT/proc/stat" <<'EOF'
cpu  100 20 30 400 5 6 7 8 0 0
EOF
cat >"$ROOT/proc/meminfo" <<'EOF'
MemTotal:        1000000 kB
MemAvailable:     500000 kB
EOF
printf '0.10 0.20 0.30 1/100 123\n' >"$ROOT/proc/loadavg"
printf '1234.56 100.00\n' >"$ROOT/proc/uptime"
printf 'up\n' >"$ROOT/sys/class/net/eth1/operstate"
printf '12345\n' >"$ROOT/sys/class/net/eth1/statistics/rx_bytes"
printf '67890\n' >"$ROOT/sys/class/net/eth1/statistics/tx_bytes"
printf 'cpu-thermal\n' >"$ROOT/sys/class/thermal/thermal_zone0/type"
printf '57900\n' >"$ROOT/sys/class/thermal/thermal_zone0/temp"
printf 'nss-top-thermal\n' >"$ROOT/sys/class/thermal/thermal_zone1/type"
printf '60100\n' >"$ROOT/sys/class/thermal/thermal_zone1/temp"
printf '1\n' >"$ROOT/sys/kernel/debug/ecm/front_end_ipv4_stop"
printf '1\n' >"$ROOT/sys/kernel/debug/ecm/front_end_ipv6_stop"
printf 'root:$1$not-a-real-hash:19000:0:99999:7:::\n' >"$ROOT/etc/shadow"
cat >"$ROOT/var/log/daed/daed.log" <<'EOF'
2026-07-30 12:00:00 INFO starting
2026-07-30 12:00:01 FATAL field LocalTcpSockops: program local_tcp_sockops: invalid argument: program of this type cannot use helper bpf_get_current_task#35
EOF

cat >"$MOCK_BIN/date" <<'EOF'
#!/bin/sh
case "${1:-}" in
	+%s) echo 1785384000 ;;
	+%Y) echo 2026 ;;
	*) echo "2026-07-30T12:00:00+0800" ;;
esac
EOF

cat >"$MOCK_BIN/ubus" <<'EOF'
#!/bin/sh
case "$*" in
	*"network.interface.wan status"*)
		echo '{"up":true,"l3_device":"eth1","ipv4-address":[{"address":"192.0.2.2"}],"ipv6-address":[{"address":"2001:db8::2"}],"dns-server":["223.5.5.5"]}'
		;;
	*"network.wireless status"*)
		echo '{"radio0":{"up":true},"radio1":{"up":true},"radio2":{"up":true}}'
		;;
	*) echo '{}' ;;
esac
EOF

cat >"$MOCK_BIN/uci" <<'EOF'
#!/bin/sh
case "$*" in
	*"firewall.@defaults[0].flow_offloading_hw"*) echo 0 ;;
	*"firewall.@defaults[0].flow_offloading"*) echo 0 ;;
	*"athena.main.iot_enabled"*) echo 1 ;;
	*"athena.main.iot_section"*) echo athena_iot ;;
	*"wireless.athena_iot.ssid"*) echo Athena-IoT ;;
	*) exit 1 ;;
esac
EOF

cat >"$MOCK_BIN/pidof" <<'EOF'
#!/bin/sh
case "${1:-}" in
	daed) echo 1234 ;;
	sysntpd|ntpd) echo 2345 ;;
	*) exit 1 ;;
esac
EOF

cat >"$MOCK_BIN/iw" <<'EOF'
#!/bin/sh
case "$*" in
	"dev")
		cat <<'OUT'
phy#2
	Interface phy2-ap0
		ssid Athena-5G
phy#1
	Interface phy1-ap0
		ssid Athena-2G
	Interface iot0
		ssid Athena-IoT
phy#0
	Interface phy0-ap0
		ssid Athena-5G-2
OUT
		;;
	"dev phy2-ap0 station dump") echo "Station 02:00:00:00:00:01 (on phy2-ap0)" ;;
	"dev phy1-ap0 station dump") echo "Station 02:00:00:00:00:02 (on phy1-ap0)" ;;
	"dev phy0-ap0 station dump") exit 0 ;;
	"dev iot0 station dump")
		echo "Station 02:00:00:00:00:03 (on iot0)"
		echo "Station 02:00:00:00:00:04 (on iot0)"
		;;
	*) exit 1 ;;
esac
EOF

cat >"$MOCK_BIN/nslookup" <<'EOF'
#!/bin/sh
exit 0
EOF
cat >"$MOCK_BIN/lsmod" <<'EOF'
#!/bin/sh
echo 'qca_nss_drv 123 0'
EOF
cat >"$MOCK_BIN/daed" <<'EOF'
#!/bin/sh
exit 0
EOF
cat >"$MOCK_BIN/logread" <<'EOF'
#!/bin/sh
exit 0
EOF
chmod +x "$MOCK_BIN"/*

export PATH="$MOCK_BIN:$PATH"
export ATHENA_ROOT="$ROOT"
export ATHENA_LIBDIR="$PROJECT_ROOT/packages/athena-runtime/files/usr/lib/athena"

. "$ATHENA_LIBDIR/common.sh"
. "$ATHENA_LIBDIR/dashboard.sh"

output="$(athena_dashboard_json)"

for token in \
	'"schema_version":1' \
	'"sampled_at":1785384000' \
	'"uptime_seconds":1234' \
	'"load_1":0.10' \
	'"load_5":0.20' \
	'"load_15":0.30' \
	'"time_synced":true' \
	'"password_set":true' \
	'"total_ticks":576' \
	'"idle_ticks":405' \
	'"total_kib":1000000' \
	'"available_kib":500000' \
	'"up":true' \
	'"device":"eth1"' \
	'"rx_bytes":12345' \
	'"tx_bytes":67890' \
	'"ipv4":true' \
	'"ipv6":true' \
	'"dns_ok":true' \
	'"radios_total":3' \
	'"radios_up":3' \
	'"clients_total":4' \
	'"iot_clients":2' \
	'"installed":true' \
	'"running":true' \
	'"error_code":"ebpf_local_tcp_sockops"' \
	'"nss_loaded":true' \
	'"ecm_ipv4_stopped":true' \
	'"ecm_ipv6_stopped":true' \
	'"flow_offload":false' \
	'"flow_offload_hw":false'
do
	printf '%s' "$output" | grep -Fq "$token" || fail "missing $token"
done

printf '%s' "$output" | grep -Fq '"thermal":[' || fail thermal_array
printf '%s' "$output" | grep -Fq '"label":"CPU"' || fail cpu_thermal
printf '%s' "$output" | grep -Fq '"label":"NSS"' || fail nss_thermal
printf '%s' "$output" | grep -Fq 'bpf_get_current_task#35' &&
	fail raw_daed_log_leaked
printf '%s' "$output" | grep -Fq 'not-a-real-hash' &&
	fail password_hash_leaked

rm -rf \
	"$ROOT/sys/class/thermal" \
	"$ROOT/sys/kernel/debug/ecm" \
	"$ROOT/var/log/daed"
rm -f "$MOCK_BIN/daed"
cat >"$MOCK_BIN/ubus" <<'EOF'
#!/bin/sh
case "$*" in
	*"network.interface.wan status"*) echo '{"up":false,"l3_device":"eth1","ipv4-address":[],"ipv6-address":[]}' ;;
	*) echo '{}' ;;
esac
EOF
chmod +x "$MOCK_BIN/ubus"
cat >"$MOCK_BIN/uci" <<'EOF'
#!/bin/sh
case "$*" in
	*"firewall.@defaults[0].flow_offloading_hw"*) echo 0 ;;
	*"firewall.@defaults[0].flow_offloading"*) echo 0 ;;
	*"athena.main.iot_enabled"*) echo 0 ;;
	*) exit 1 ;;
esac
EOF
chmod +x "$MOCK_BIN/uci"

missing="$(athena_dashboard_json)"
for token in \
	'"thermal":[]' \
	'"ipv6":false' \
	'"iot_clients":null' \
	'"installed":false' \
	'"running":false' \
	'"error_code":null' \
	'"ecm_ipv4_stopped":null' \
	'"ecm_ipv6_stopped":null'
do
	printf '%s' "$missing" | grep -Fq "$token" || fail "missing-data contract lacks $token"
done

printf 'PASS: dashboard\n'
