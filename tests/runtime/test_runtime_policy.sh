#!/bin/sh
set -eu

fail() { echo "FAIL: $*" >&2; exit 1; }
ROOT="$(mktemp -d)"
trap 'rm -rf "$ROOT"' EXIT
export ATHENA_ROOT="$ROOT"
export ATHENA_LIBDIR="${PROJECT_ROOT}/packages/athena-runtime/files/usr/lib/athena"
export ATHENA_ECM_WAIT_SECONDS=0
BIN="${PROJECT_ROOT}/packages/athena-runtime/files/usr/bin/athena-runtime"

mkdir -p "$ROOT/sys/kernel/debug/ecm" "$ROOT/sys/devices/system/cpu/cpufreq/policy0"
printf '0\n' >"$ROOT/sys/kernel/debug/ecm/front_end_ipv4_stop"
printf '0\n' >"$ROOT/sys/kernel/debug/ecm/front_end_ipv6_stop"
printf 'ondemand\n' >"$ROOT/sys/devices/system/cpu/cpufreq/policy0/scaling_governor"

"$BIN" apply
[ "$(cat "$ROOT/sys/kernel/debug/ecm/front_end_ipv4_stop")" = 1 ] || fail ipv4
[ "$(cat "$ROOT/sys/kernel/debug/ecm/front_end_ipv6_stop")" = 1 ] || fail ipv6
[ "$(cat "$ROOT/sys/devices/system/cpu/cpufreq/policy0/scaling_governor")" = performance ] || fail governor
"$BIN" apply
"$BIN" status | grep -q '^ecm_ipv4_stop=1$' || fail status
! grep -q 'defunct_all\|rmmod\|/proc/irq' "$BIN" || fail forbidden
echo "PASS: runtime-policy"
