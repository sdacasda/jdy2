#!/bin/sh
set -eu

fail() { echo "FAIL: $*" >&2; exit 1; }
ROOT="$(mktemp -d)"
trap 'rm -rf "$ROOT"' EXIT
ATHENA_ROOT="$ROOT"
export ATHENA_ROOT
. "${PROJECT_ROOT}/packages/athena-runtime/files/usr/lib/athena/common.sh"

[ "$(athena_root /etc/config/athena)" = "$ROOT/etc/config/athena" ] || fail athena_root
athena_is_ipv4 223.5.5.5 || fail valid_ipv4
! athena_is_ipv4 999.5.5.5 || fail invalid_ipv4
athena_is_mac AA:BB:CC:DD:EE:FF || fail valid_mac
! athena_is_mac AA:BB:CC:DD:EE || fail invalid_mac
printf '%s\n' 'vless://user@example.com token=abcdef123456' | # SECURITY-SCAN-ALLOW
    athena_redact | grep -q 'REDACTED' || fail redact

mkdir -p "$ROOT/etc"
printf 'atomic\n' | athena_atomic_write /etc/example
[ "$(cat "$ROOT/etc/example")" = atomic ] || fail atomic_write

athena_lock common-test || fail lock
! athena_lock common-test || fail duplicate_lock
athena_unlock
echo "PASS: common"
