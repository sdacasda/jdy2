#!/bin/sh
set -eu

ROOT="$(mktemp -d)"
trap 'rm -rf "$ROOT"' EXIT
mkdir -p "$ROOT/etc/config" "$ROOT/etc/athena/generated" "$ROOT/sys/kernel/debug/ecm" "$ROOT/var/lib/athena"
printf "config athena 'main'\n\toption enabled '0'\n" >"$ROOT/etc/config/athena"
printf '1\n' >"$ROOT/sys/kernel/debug/ecm/front_end_ipv4_stop"
printf '1\n' >"$ROOT/sys/kernel/debug/ecm/front_end_ipv6_stop"

export ATHENA_ROOT="$ROOT"
export PROJECT_ROOT="${PROJECT_ROOT:?}"
export ATHENA_LIBDIR="$PROJECT_ROOT/packages/athena-runtime/files/usr/lib/athena"
export ATHENA_NGINX_OK=1
export ATHENA_WEB_PORTS_OK=1
export ATHENA_RECOVERY_WEB_OK=1
export ATHENA_DAED_ENABLED=0
export ATHENA_DAED_RUNNING=0
export ATHENA_DAED_API_REACHABLE=0
BIN="$PROJECT_ROOT/packages/athena-runtime/files/usr/bin/athena-health"

output="$(sh "$BIN" --json)"
printf '%s' "$output" | grep -q '"id":"setup_state"'
printf '%s' "$output" | grep -q '"status":"WARN"'
for id in nginx web_ports recovery_web; do
	printf '%s' "$output" | grep -q "\"id\":\"$id\",\"severity\":\"critical\",\"status\":\"PASS\""
done
for id in daed_enabled daed_process daed_api; do
	printf '%s' "$output" | grep -q "\"id\":\"$id\",\"severity\":\"advisory\",\"status\":\"WARN\""
done

export ATHENA_DAED_ENABLED=1
export ATHENA_DAED_RUNNING=0
export ATHENA_DAED_API_REACHABLE=0
printf '0\n' >"$ROOT/sys/kernel/debug/ecm/front_end_ipv4_stop"
printf '0\n' >"$ROOT/sys/kernel/debug/ecm/front_end_ipv6_stop"
set +e
normal_output="$(sh "$BIN" --json)"
normal_code=$?
polluted_output="$(ATHENA_HEALTH_STRICT=1 sh "$BIN" --json)"
polluted_code=$?
set -e
[ "$normal_code" -eq 0 ]
[ "$polluted_code" -eq 0 ]
[ "$normal_output" = "$polluted_output" ]

printf '1\n' >"$ROOT/sys/kernel/debug/ecm/front_end_ipv4_stop"
printf '1\n' >"$ROOT/sys/kernel/debug/ecm/front_end_ipv6_stop"
printf 'STATE=complete\n' >"$ROOT/var/lib/athena/setup-state"
export ATHENA_DAED_ENABLED=1
export ATHENA_DAED_RUNNING=1
export ATHENA_DAED_API_REACHABLE=0
set +e
failed_output="$(sh "$BIN" --json)"
failed_code=$?
set -e
[ "$failed_code" -eq 2 ]
printf '%s' "$failed_output" | grep -q '"id":"daed_api","severity":"critical","status":"FAIL"'

set +e
sh "$BIN" --unknown >/dev/null 2>&1
code=$?
set -e
[ "$code" -eq 64 ]

printf 'PASS: health\n'
