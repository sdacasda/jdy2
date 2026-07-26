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
BIN="$PROJECT_ROOT/packages/athena-runtime/files/usr/bin/athena-health"

output="$(sh "$BIN" --json)"
printf '%s' "$output" | grep -q '"id":"setup_state"'
printf '%s' "$output" | grep -q '"status":"WARN"'

set +e
sh "$BIN" --unknown >/dev/null 2>&1
code=$?
set -e
[ "$code" -eq 64 ]

printf 'PASS: health\n'
