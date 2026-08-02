#!/bin/sh
set -eu

fail() { echo "FAIL: $*" >&2; exit 1; }
ROOT="$(mktemp -d)"
trap 'rm -rf "$ROOT"' EXIT
export ATHENA_ROOT="$ROOT"
export ATHENA_LIBDIR="${PROJECT_ROOT}/packages/athena-runtime/files/usr/lib/athena"
BIN="${PROJECT_ROOT}/packages/athena-runtime/files/usr/bin"

mkdir -p "$ROOT/etc/config" "$ROOT/etc/daed" "$ROOT/etc/nginx/conf.d"
printf 'network-original\n' >"$ROOT/etc/config/network"
printf 'database-original\n' >"$ROOT/etc/daed/wing.db"
printf 'locations-original\n' >"$ROOT/etc/nginx/conf.d/athena-daed.locations"
printf 'nginx-original\n' >"$ROOT/etc/config/nginx"
printf 'uhttpd-original\n' >"$ROOT/etc/config/uhttpd"
printf 'daed-service-original\n' >"$ROOT/etc/config/daed"
backup="$("$BIN/athena-backup" rollback)"
id="${backup##*/}"

printf 'database-modified\n' >"$ROOT/etc/daed/wing.db"
"$BIN/athena-rollback" --component daed "$id"
[ "$(cat "$ROOT/etc/daed/wing.db")" = database-original ] || fail daed_restore
[ "$(cat "$ROOT/etc/config/network")" = network-original ] || fail unrelated_config

printf 'database-after-daed-rollback\n' >"$ROOT/etc/daed/wing.db"
printf 'locations-modified\n' >"$ROOT/etc/nginx/conf.d/athena-daed.locations"
printf 'nginx-modified\n' >"$ROOT/etc/config/nginx"
printf 'uhttpd-modified\n' >"$ROOT/etc/config/uhttpd"
printf 'daed-service-modified\n' >"$ROOT/etc/config/daed"
"$BIN/athena-rollback" --component web "$id"
[ "$(cat "$ROOT/etc/nginx/conf.d/athena-daed.locations")" = locations-original ] || fail web_locations_restore
[ "$(cat "$ROOT/etc/config/nginx")" = nginx-original ] || fail nginx_config_restore
[ "$(cat "$ROOT/etc/config/uhttpd")" = uhttpd-original ] || fail uhttpd_config_restore
[ "$(cat "$ROOT/etc/config/daed")" = daed-service-original ] || fail daed_service_restore
[ "$(cat "$ROOT/etc/daed/wing.db")" = database-after-daed-rollback ] || fail web_touched_wing_db
! "$BIN/athena-rollback" '../invalid' >/dev/null 2>&1 || fail traversal
echo "PASS: rollback"
