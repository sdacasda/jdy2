#!/bin/sh

fail=0

result() {
	status="$1"
	label="$2"
	echo "[$status] $label"
	[ "$status" != FAIL ] || fail=1
}

check() {
	label="$1"
	severity="$2"
	shift 2
	if "$@" >/dev/null 2>&1; then
		result PASS "$label"
	else
		result "$severity" "$label"
	fi
}

http_response() {
	url="$1"
	if command -v wget >/dev/null 2>&1; then
		response="$(wget --no-check-certificate -S -O /dev/null -T 5 "$url" 2>&1 || true)"
		printf '%s\n' "$response" | grep -Eq 'HTTP/[0-9.]+[[:space:]]+[0-9]{3}'
		return
	fi
	return 1
}

lan_address_ok() {
	[ "$(uci -q get network.lan.ipaddr)" = 192.168.50.1 ]
}

daed_defaults_ok() {
	[ "$(uci -q get daed.config.listen_addr)" = 127.0.0.1:2023 ] &&
		[ "$(uci -q get daed.config.enabled)" = 0 ]
}

recovery_listener_ok() {
	uci -q show uhttpd.recovery | grep -q "listen_http='192.168.50.1:8080'" &&
		[ -z "$(uci -q get uhttpd.main.listen_http)" ] &&
		[ -z "$(uci -q get uhttpd.main.listen_https)" ]
}

daed_not_exposed() {
	command -v ss >/dev/null 2>&1 || return 0
	listeners="$(ss -lnt 2>/dev/null || true)"
	# These wildcard forms are intentionally forbidden: 0.0.0.0:2023 and [::]:2023.
	! printf '%s\n' "$listeners" | grep -Eq '0\.0\.0\.0:2023|\[::\]:2023|\*:2023'
}

check "LAN is 192.168.50.1" FAIL lan_address_ok
check "DAED is disabled and loopback-only by default" FAIL daed_defaults_ok
check "Athena commands are installed" FAIL sh -c 'command -v athena-setup && command -v athena-health && command -v athena-iot'
check "Argon is installed" FAIL test -d /www/luci-static/argon
check "Nginx configuration is valid" FAIL nginx -t
check "Nginx primary Web process is running" FAIL pidof nginx
check "Recovery uHTTPd owns only 192.168.50.1:8080" FAIL recovery_listener_ok
check "Recovery page responds" FAIL http_response http://192.168.50.1:8080/athena-recovery.html
check "Primary LuCI responds through Nginx" FAIL http_response https://127.0.0.1/cgi-bin/luci/
check "DAED port 2023 is not exposed on wildcard listeners" FAIL daed_not_exposed
check "BTF is available" FAIL sh -c 'test -r /sys/kernel/btf/vmlinux || test -r /usr/lib/debug/boot/vmlinux'
check "Three wireless PHYs are present" WARN sh -c '[ "$(find /sys/class/ieee80211 -mindepth 1 -maxdepth 1 2>/dev/null | wc -l)" -ge 3 ]'

if pidof daed >/dev/null 2>&1; then
	check "DAED loopback GraphQL responds" FAIL http_response http://127.0.0.1:2023/graphql
	check "DAED same-origin GraphQL responds" FAIL http_response https://127.0.0.1/athena-daed/graphql
else
	result WARN "DAED same-origin proxy is unavailable while DAED is safely off"
fi

athena-health --verbose || fail=1
exit "$fail"
