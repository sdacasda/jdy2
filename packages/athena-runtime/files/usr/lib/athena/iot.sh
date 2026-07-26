#!/bin/sh

athena_iot_validate() {
	ssid="$1"; key="$2"; channel="$3"
	[ -n "$ssid" ] && [ "${#ssid}" -le 32 ] || return 1
	[ "${#key}" -ge 8 ] && [ "${#key}" -le 63 ] || return 1
	case "$channel" in 1|6|11) ;; *) return 1 ;; esac
	case "$ssid$key" in *'
'*) return 1 ;; esac
}

athena_iot_find_radio() {
	if [ -n "${ATHENA_IOT_RADIO:-}" ]; then printf '%s\n' "$ATHENA_IOT_RADIO"; return 0; fi
	uci show wireless 2>/dev/null | awk -F'[.=]' '
		/\.band='\''2g'\''/ { print $2; exit }
		/\.hwmode='\''11g'\''/ { fallback=$2 }
		END { if (!NR && fallback) print fallback }
	'
}

athena_iot_apply() {
	ssid="$1"; key="$2"; channel="$3"
	athena_iot_validate "$ssid" "$key" "$channel" || athena_die "Invalid IoT SSID, passphrase, or channel (use 1, 6, or 11)."
	radio="$(athena_iot_find_radio)"
	[ -n "$radio" ] || athena_die "No unambiguous 2.4 GHz radio was found."
	section="$(athena_uci_get athena.main.iot_section athena_iot)"
	backup_id="$(athena_backup_create iot-wifi)"
	uci -q batch <<UCI
set wireless.$radio.country='CN'
set wireless.$radio.channel='$channel'
set wireless.$radio.htmode='HT20'
set wireless.$section='wifi-iface'
set wireless.$section.device='$radio'
set wireless.$section.mode='ap'
set wireless.$section.network='lan'
set wireless.$section.ssid='$ssid'
set wireless.$section.encryption='psk2+ccmp'
set wireless.$section.key='$key'
set wireless.$section.ieee80211w='0'
set wireless.$section.ieee80211r='0'
set wireless.$section.ieee80211k='0'
set wireless.$section.ieee80211v='0'
set wireless.$section.wmm='1'
set wireless.$section.hidden='0'
set wireless.$section.isolate='0'
set wireless.$section.he_su_beamformer='0'
set wireless.$section.disabled='0'
set athena.main.iot_enabled='1'
set athena.main.iot_channel='$channel'
commit wireless
commit athena
UCI
	wifi reload >/dev/null 2>&1 || {
		athena_log ERROR "Wi-Fi reload failed; backup is $backup_id"
		return 1
	}
	printf 'IoT compatibility network applied; backup=%s\n' "$backup_id"
}

athena_iot_status() {
	enabled="$(athena_uci_get athena.main.iot_enabled 0)"
	section="$(athena_uci_get athena.main.iot_section athena_iot)"
	printf 'enabled=%s\nsection=%s\nchannel=%s\n' "$enabled" "$section" "$(athena_uci_get athena.main.iot_channel 6)"
	[ "$enabled" != 1 ] || printf 'security=wpa2-psk-aes\nwidth=20MHz\npmf=off\nwifi6=off\n'
}

athena_iot_diagnose() {
	athena_iot_status
	printf 'radio=%s\n' "$(athena_iot_find_radio 2>/dev/null || echo unavailable)"
	printf 'associated_stations=%s\n' "$(iw dev 2>/dev/null | grep -c 'Station ' || true)"
	printf 'dhcp_lease_count=%s\n' "$(wc -l <"$(athena_root /tmp/dhcp.leases)" 2>/dev/null || echo 0)"
	logread 2>/dev/null | grep -Ei 'hostapd.*(fail|reject)|netifd.*wireless.*(fail|down)' | tail -n 20 |
		sed -E 's/([[:xdigit:]]{2}:){5}[[:xdigit:]]{2}/REDACTED-MAC/g'
}
