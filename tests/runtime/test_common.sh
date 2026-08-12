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

control_value="$(printf '%b' 'a\tb\rc')"
escaped="$(printf '%s' "$control_value" | athena_json_escape)"
[ "$escaped" = 'a\tb\rc' ] || fail json_control_escape
printf '{"value":"%s"}' "$escaped" | "${PYTHON:?set PYTHON}" -c 'import json,sys; assert json.load(sys.stdin)["value"] == "a\tb\rc"' || fail json_control_valid
escaped_lf="$(printf 'a\n\n' | athena_json_escape)"
[ "$escaped_lf" = 'a\n\n' ] || fail json_terminal_newlines
[ "$(athena_json_escape '')" = '' ] || fail json_empty
all_controls="$(awk 'BEGIN { for (i=1; i<32; i++) printf "%c", i }')"
escaped_controls="$(printf '%s' "$all_controls" | athena_json_escape)"
printf '{"value":"%s"}' "$escaped_controls" | "${PYTHON:?set PYTHON}" -c 'import json,sys; assert json.load(sys.stdin)["value"] == "".join(map(chr, range(1, 32)))' || fail json_all_controls
us_newline="$(printf '%b' 'a\037\nb')"
[ "$(athena_json_escape "$us_newline")" = 'a\u001f\nb' ] || fail json_unit_separator
echo "PASS: common"
