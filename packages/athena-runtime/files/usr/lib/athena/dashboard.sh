#!/bin/sh

athena_dashboard_number() {
	value="${1:-}"
	case "$value" in
		""|*[!0-9.-]*) printf 'null' ;;
		*) printf '%s' "$value" ;;
	esac
}

athena_dashboard_boolean() {
	case "${1:-}" in
		1|true|yes|up) printf 'true' ;;
		0|false|no|down) printf 'false' ;;
		*) printf 'null' ;;
	esac
}

athena_dashboard_string() {
	if [ -z "${1:-}" ]; then
		printf 'null'
	else
		printf '"%s"' "$(athena_json_escape "$1")"
	fi
}

athena_dashboard_read() {
	path="$(athena_root "$1")"
	[ -r "$path" ] || return 1
	head -n 1 "$path" 2>/dev/null
}

athena_dashboard_cpu() {
	stat_path="$(athena_root /proc/stat)"
	if [ -r "$stat_path" ]; then
		set -- $(awk '
			$1 == "cpu" {
				total = 0
				for (i = 2; i <= NF; i++) total += $i
				print total, $5 + $6
				exit
			}
		' "$stat_path" 2>/dev/null)
		cpu_total="${1:-}"
		cpu_idle="${2:-}"
	else
		cpu_total=""
		cpu_idle=""
	fi
	printf '"cpu":{"total_ticks":%s,"idle_ticks":%s}' \
		"$(athena_dashboard_number "$cpu_total")" \
		"$(athena_dashboard_number "$cpu_idle")"
}

athena_dashboard_memory() {
	meminfo="$(athena_root /proc/meminfo)"
	if [ -r "$meminfo" ]; then
		mem_total="$(awk '$1 == "MemTotal:" { print $2; exit }' "$meminfo" 2>/dev/null)"
		mem_available="$(awk '$1 == "MemAvailable:" { print $2; exit }' "$meminfo" 2>/dev/null)"
	else
		mem_total=""
		mem_available=""
	fi
	printf '"memory":{"total_kib":%s,"available_kib":%s}' \
		"$(athena_dashboard_number "$mem_total")" \
		"$(athena_dashboard_number "$mem_available")"
}

athena_dashboard_wan() {
	wan_json="$(ubus call network.interface.wan status 2>/dev/null || true)"
	wan6_json="$(ubus call network.interface.wan6 status 2>/dev/null || true)"
	wan_compact="$(printf '%s' "$wan_json" | tr -d '\n')"
	wan6_compact="$(printf '%s' "$wan6_json" | tr -d '\n')"
	wan_device="$(printf '%s' "$wan_compact" |
		sed -n 's/.*"l3_device"[[:space:]]*:[[:space:]]*"\([^"]*\)".*/\1/p' |
		head -n 1)"
	if printf '%s' "$wan_compact" |
		grep -Eq '"up"[[:space:]]*:[[:space:]]*true'; then
		wan_up=1
	else
		wan_up=0
	fi
	if printf '%s' "$wan_compact" |
		grep -Eq '"ipv4-address"[[:space:]]*:[[:space:]]*\[[[:space:]]*\{'; then
		wan_ipv4=1
	else
		wan_ipv4=0
	fi
	if printf '%s%s' "$wan_compact" "$wan6_compact" |
		grep -Eq '"ipv6-address"[[:space:]]*:[[:space:]]*\[[[:space:]]*\{'; then
		wan_ipv6=1
	elif printf '%s%s' "$wan_compact" "$wan6_compact" |
		grep -Eq '"ipv6-prefix"[[:space:]]*:[[:space:]]*\[[[:space:]]*\{'; then
		wan_ipv6=1
	else
		wan_ipv6=0
	fi
	if printf '%s' "$wan_compact" |
		grep -Eq '"dns-server"[[:space:]]*:[[:space:]]*\[[[:space:]]*"'; then
		wan_dns=1
	else
		wan_dns=0
	fi

	wan_rx=""
	wan_tx=""
	if [ -n "$wan_device" ]; then
		wan_rx="$(athena_dashboard_read "/sys/class/net/$wan_device/statistics/rx_bytes" || true)"
		wan_tx="$(athena_dashboard_read "/sys/class/net/$wan_device/statistics/tx_bytes" || true)"
	fi

	printf '"wan":{"up":%s,"device":%s,"rx_bytes":%s,"tx_bytes":%s,"ipv4":%s,"ipv6":%s,"dns_ok":%s}' \
		"$(athena_dashboard_boolean "$wan_up")" \
		"$(athena_dashboard_string "$wan_device")" \
		"$(athena_dashboard_number "$wan_rx")" \
		"$(athena_dashboard_number "$wan_tx")" \
		"$(athena_dashboard_boolean "$wan_ipv4")" \
		"$(athena_dashboard_boolean "$wan_ipv6")" \
		"$(athena_dashboard_boolean "$wan_dns")"
}

athena_dashboard_thermal_label() {
	case "$1" in
		cpu*|*cpu*) printf 'cpu|CPU' ;;
		*nss*) printf 'nss|NSS' ;;
		*wcss*|*wifi*|*radio*) printf 'wifi|Wi-Fi' ;;
		*) printf 'other|Thermal' ;;
	esac
}

athena_dashboard_thermal() {
	thermal_root="$(athena_root /sys/class/thermal)"
	first=1
	printf '"thermal":['
	for zone in "$thermal_root"/thermal_zone*; do
		[ -d "$zone" ] || continue
		type="$(cat "$zone/type" 2>/dev/null || true)"
		temp="$(cat "$zone/temp" 2>/dev/null || true)"
		[ -n "$type" ] && [ -n "$temp" ] || continue
		mapping="$(athena_dashboard_thermal_label "$type")"
		id="${mapping%%|*}"
		label="${mapping#*|}"
		if [ "$first" -eq 0 ]; then printf ','; fi
		first=0
		printf '{"id":"%s","label":"%s","millicelsius":%s}' \
			"$(athena_json_escape "$id")" \
			"$(athena_json_escape "$label")" \
			"$(athena_dashboard_number "$temp")"
	done
	printf ']'
}

athena_dashboard_wireless() {
	wireless_json="$(ubus call network.wireless status 2>/dev/null || true)"
	wireless_compact="$(printf '%s' "$wireless_json" | tr -d '\n')"
	radios_total="$(printf '%s' "$wireless_compact" |
		grep -Eo '"radio[0-9]+"' 2>/dev/null | sort -u | wc -l | tr -d ' ')"
	radios_up="$(printf '%s' "$wireless_compact" |
		grep -Eo '"up"[[:space:]]*:[[:space:]]*true' 2>/dev/null |
		wc -l | tr -d ' ')"

	iw_state="$(iw dev 2>/dev/null || true)"
	interfaces="$(printf '%s\n' "$iw_state" |
		awk '$1 == "Interface" { print $2 }')"
	clients_total=0
	for iface in $interfaces; do
		count="$(iw dev "$iface" station dump 2>/dev/null |
			grep -c '^Station ' || true)"
		clients_total=$((clients_total + count))
	done

	iot_enabled="$(athena_uci_get athena.main.iot_enabled 0)"
	iot_clients_json=null
	if [ "$iot_enabled" = 1 ]; then
		iot_section="$(athena_uci_get athena.main.iot_section athena_iot)"
		iot_ssid="$(athena_uci_get "wireless.$iot_section.ssid" "")"
		iot_iface="$(printf '%s\n' "$iw_state" |
			awk -v wanted="$iot_ssid" '
				$1 == "Interface" { iface=$2 }
				$1 == "ssid" {
					ssid=$0
					sub(/^[[:space:]]*ssid[[:space:]]+/, "", ssid)
					if (ssid == wanted) { print iface; exit }
				}
			')"
		if [ -n "$iot_iface" ]; then
			iot_clients="$(iw dev "$iot_iface" station dump 2>/dev/null |
				grep -c '^Station ' || true)"
			iot_clients_json="$(athena_dashboard_number "$iot_clients")"
		else
			iot_clients_json=0
		fi
	fi

	printf '"wireless":{"radios_total":%s,"radios_up":%s,"clients_total":%s,"iot_clients":%s}' \
		"$(athena_dashboard_number "$radios_total")" \
		"$(athena_dashboard_number "$radios_up")" \
		"$(athena_dashboard_number "$clients_total")" \
		"$iot_clients_json"
}

athena_dashboard_daed_error() {
	daed_log="$(athena_root /var/log/daed/daed.log)"
	if [ -r "$daed_log" ]; then
		recent="$(tail -n 200 "$daed_log" 2>/dev/null || true)"
	else
		recent="$(logread -e daed 2>/dev/null | tail -n 200 || true)"
	fi
	if printf '%s' "$recent" |
		grep -Eq 'LocalTcpSockops|local_tcp_sockops|bpf_get_current_task#35'; then
		printf 'ebpf_local_tcp_sockops'
	elif printf '%s' "$recent" | grep -Eqi 'verifier|load eBPF objects'; then
		printf 'ebpf_verifier'
	elif printf '%s' "$recent" | grep -Eqi 'FATAL|startup failure|failed to start'; then
		printf 'startup_failure'
	fi
}

athena_dashboard_daed() {
	if command -v daed >/dev/null 2>&1; then
		daed_installed=1
	else
		daed_installed=0
	fi
	if [ "$daed_installed" -eq 1 ] && pidof daed >/dev/null 2>&1; then
		daed_running=1
	else
		daed_running=0
	fi
	daed_error="$(athena_dashboard_daed_error)"
	printf '"daed":{"installed":%s,"running":%s,"error_code":%s,"error_at":null}' \
		"$(athena_dashboard_boolean "$daed_installed")" \
		"$(athena_dashboard_boolean "$daed_running")" \
		"$(athena_dashboard_string "$daed_error")"
}

athena_dashboard_acceleration() {
	if lsmod 2>/dev/null | grep -Eq '(^|[[:space:]])qca_nss'; then
		nss_loaded=1
	else
		nss_loaded=0
	fi
	ecm4="$(athena_dashboard_read /sys/kernel/debug/ecm/front_end_ipv4_stop || true)"
	ecm6="$(athena_dashboard_read /sys/kernel/debug/ecm/front_end_ipv6_stop || true)"
	flow="$(athena_uci_get 'firewall.@defaults[0].flow_offloading' "")"
	flow_hw="$(athena_uci_get 'firewall.@defaults[0].flow_offloading_hw' "")"
	printf '"acceleration":{"nss_loaded":%s,"ecm_ipv4_stopped":%s,"ecm_ipv6_stopped":%s,"flow_offload":%s,"flow_offload_hw":%s}' \
		"$(athena_dashboard_boolean "$nss_loaded")" \
		"$(athena_dashboard_boolean "$ecm4")" \
		"$(athena_dashboard_boolean "$ecm6")" \
		"$(athena_dashboard_boolean "$flow")" \
		"$(athena_dashboard_boolean "$flow_hw")"
}

athena_dashboard_system() {
	uptime="$(athena_dashboard_read /proc/uptime 2>/dev/null |
		awk '{ print int($1) }' || true)"
	loadavg_path="$(athena_root /proc/loadavg)"
	if [ -r "$loadavg_path" ]; then
		set -- $(head -n 1 "$loadavg_path" 2>/dev/null)
		load1="${1:-}"
		load5="${2:-}"
		load15="${3:-}"
	else
		load1=""
		load5=""
		load15=""
	fi
	year="$(date +%Y 2>/dev/null || echo 0)"
	case "$year" in
		*[!0-9]*|"") time_valid=0 ;;
		*) [ "$year" -ge 2020 ] && time_valid=1 || time_valid=0 ;;
	esac
	if [ "$time_valid" -eq 1 ] &&
		(pidof sysntpd >/dev/null 2>&1 || pidof ntpd >/dev/null 2>&1); then
		time_synced=1
	else
		time_synced=0
	fi

	password_set=0
	shadow="$(athena_root /etc/shadow)"
	if [ -r "$shadow" ]; then
		root_hash="$(awk -F: '$1 == "root" { print $2; exit }' "$shadow" 2>/dev/null)"
		case "$root_hash" in
			""|"!"|"*"|"x") password_set=0 ;;
			*) password_set=1 ;;
		esac
	fi

	printf '"system":{"uptime_seconds":%s,"load_1":%s,"load_5":%s,"load_15":%s,"time_synced":%s,"password_set":%s}' \
		"$(athena_dashboard_number "$uptime")" \
		"$(athena_dashboard_number "$load1")" \
		"$(athena_dashboard_number "$load5")" \
		"$(athena_dashboard_number "$load15")" \
		"$(athena_dashboard_boolean "$time_synced")" \
		"$(athena_dashboard_boolean "$password_set")"
}

athena_dashboard_json() {
	sampled_at="$(date +%s 2>/dev/null || true)"
	printf '{'
	printf '"schema_version":1,"sampled_at":%s,' \
		"$(athena_dashboard_number "$sampled_at")"
	athena_dashboard_system
	printf ','
	athena_dashboard_cpu
	printf ','
	athena_dashboard_memory
	printf ','
	athena_dashboard_wan
	printf ','
	athena_dashboard_thermal
	printf ','
	athena_dashboard_wireless
	printf ','
	athena_dashboard_daed
	printf ','
	athena_dashboard_acceleration
	printf '}\n'
}
