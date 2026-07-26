#!/bin/sh
set -eu

fail() { echo "FAIL: $*" >&2; exit 1; }
ROOT="$(mktemp -d)"
trap 'rm -rf "$ROOT"' EXIT
export ATHENA_ROOT="$ROOT"
export ATHENA_LIBDIR="${PROJECT_ROOT}/packages/athena-runtime/files/usr/lib/athena"
BIN="${PROJECT_ROOT}/packages/athena-runtime/files/usr/bin"

mkdir -p "$ROOT/etc/config" "$ROOT/etc/daed"
printf 'network-original\n' >"$ROOT/etc/config/network"
printf 'database-original\n' >"$ROOT/etc/daed/wing.db"
backup="$("$BIN/athena-backup" rollback)"
id="${backup##*/}"

printf 'database-modified\n' >"$ROOT/etc/daed/wing.db"
"$BIN/athena-rollback" --component daed "$id"
[ "$(cat "$ROOT/etc/daed/wing.db")" = database-original ] || fail daed_restore
[ "$(cat "$ROOT/etc/config/network")" = network-original ] || fail unrelated_config
! "$BIN/athena-rollback" '../invalid' >/dev/null 2>&1 || fail traversal
echo "PASS: rollback"
