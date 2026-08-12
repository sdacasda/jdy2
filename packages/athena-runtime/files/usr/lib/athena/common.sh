#!/bin/sh

ATHENA_ROOT="${ATHENA_ROOT:-/}"
ATHENA_LOCK_PATH=""

athena_root() {
	case "$1" in
		/*) printf '%s%s\n' "${ATHENA_ROOT%/}" "$1" ;;
		*) printf '%s/%s\n' "${ATHENA_ROOT%/}" "$1" ;;
	esac
}

athena_log() {
	level="$1"
	shift
	message="$(printf '%s' "$*" | athena_redact)"
	printf '%s [%s] %s\n' "$(date '+%Y-%m-%dT%H:%M:%S%z' 2>/dev/null || printf unknown)" "$level" "$message" >&2
}

athena_die() {
	athena_log ERROR "$*"
	exit 1
}

athena_redact() {
	sed -E \
		-e 's#((vless|vmess|trojan|hysteria2?|tuic|ss)://)[^[:space:]]+#\1REDACTED#gI' \
		-e 's#((token|password|passwd|private_key|uuid)[[:space:]]*[:=][[:space:]]*)[^[:space:],;]+#\1REDACTED#gI'
}

athena_lock() {
	name="$1"
	lock_root="$(athena_root /var/lock)"
	mkdir -p "$lock_root"
	ATHENA_LOCK_PATH="$lock_root/athena-$name.lock"
	mkdir "$ATHENA_LOCK_PATH" 2>/dev/null
}

athena_unlock() {
	if [ -n "$ATHENA_LOCK_PATH" ] && [ -d "$ATHENA_LOCK_PATH" ]; then
		rmdir "$ATHENA_LOCK_PATH" 2>/dev/null || true
	fi
	ATHENA_LOCK_PATH=""
}

athena_atomic_write() {
	target="$(athena_root "$1")"
	parent="$(dirname "$target")"
	mkdir -p "$parent"
	tmp="$parent/.athena.$$.tmp"
	umask 077
	if ! cat >"$tmp"; then
		rm -f "$tmp"
		return 1
	fi
	mv -f "$tmp" "$target"
}

athena_uci_get() {
	key="$1"
	default="${2:-}"
	if command -v uci >/dev/null 2>&1; then
		value="$(uci -q get "$key" 2>/dev/null || true)"
	else
		value=""
	fi
	[ -n "$value" ] && printf '%s\n' "$value" || printf '%s\n' "$default"
}

athena_is_ipv4() {
	printf '%s\n' "$1" | awk -F. '
		NF != 4 { bad=1 }
		{
			for (i=1; i<=4; i++)
				if ($i !~ /^[0-9]+$/ || $i < 0 || $i > 255) bad=1
		}
		END { exit bad ? 1 : 0 }
	'
}

athena_is_mac() {
	printf '%s\n' "$1" | grep -Eq '^([[:xdigit:]]{2}:){5}[[:xdigit:]]{2}$'
}

athena_is_hostname() {
	case "$1" in
		""|*[^A-Za-z0-9.-]*|.*|*..*|*.) return 1 ;;
	esac
	printf '%s\n' "$1" | grep -Eq '^[A-Za-z0-9]([A-Za-z0-9.-]*[A-Za-z0-9])?$'
}

athena_json_escape() {
	# Work byte-wise: printable UTF-8 passes through unchanged while every JSON
	# control character is encoded without relying on a non-BusyBox runtime.
	if [ "$#" -gt 0 ]; then
		printf '%s' "$1"
	else
		cat
	fi | od -An -v -t u1 | LC_ALL=C awk '
		{
			for (i = 1; i <= NF; i++) {
				b = $i
				if (b == 34) printf "\\\""
				else if (b == 92) printf "\\\\"
				else if (b == 8) printf "\\b"
				else if (b == 9) printf "\\t"
				else if (b == 10) printf "\\n"
				else if (b == 12) printf "\\f"
				else if (b == 13) printf "\\r"
				else if (b < 32) printf "\\u%04x", b
				else printf "%c", b
			}
		}'
}

athena_daed_graphql_reachable() {
	url="${ATHENA_DAED_GRAPHQL_URL:-http://127.0.0.1:2023/graphql}"
	payload='{"query":"query AthenaHealth { __typename }"}'
	if command -v wget >/dev/null 2>&1; then
		response="$(wget -S -O - -T 2 \
			--header='Content-Type: application/json' \
			--post-data="$payload" "$url" 2>&1 || true)"
		if printf '%s\n' "$response" | grep -Eq \
			'"(data|errors)"[[:space:]]*:|HTTP/[0-9.]+[[:space:]]+[0-9]{3}'; then
			return 0
		fi
	fi
	if command -v nc >/dev/null 2>&1; then
		length="$(printf '%s' "$payload" | wc -c | tr -d ' ')"
		{
			printf 'POST /graphql HTTP/1.0\r\n'
			printf 'Host: localhost\r\n'
			printf 'Content-Type: application/json\r\n'
			printf 'Content-Length: %s\r\n\r\n' "$length"
			printf '%s' "$payload"
		} | nc -w 2 127.0.0.1 2023 2>/dev/null |
			grep -Eq '^HTTP/[0-9.]+[[:space:]]+[0-9]{3}'
		return
	fi
	return 1
}
