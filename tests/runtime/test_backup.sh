#!/bin/sh
set -eu

fail() { echo "FAIL: $*" >&2; exit 1; }
ROOT="$(mktemp -d)"
trap 'rm -rf "$ROOT"' EXIT
export ATHENA_ROOT="$ROOT"
export ATHENA_LIBDIR="${PROJECT_ROOT}/packages/athena-runtime/files/usr/lib/athena"
BIN="${PROJECT_ROOT}/packages/athena-runtime/files/usr/bin"

mkdir -p "$ROOT/etc/config" "$ROOT/etc/daed" "$ROOT/etc/nginx/conf.d" "$ROOT/var/lib/athena"
printf 'network-original\n' >"$ROOT/etc/config/network"
printf 'database-original\n' >"$ROOT/etc/daed/wing.db"
printf 'web-original\n' >"$ROOT/etc/nginx/conf.d/athena.conf"
printf 'state-original\n' >"$ROOT/var/lib/athena/setup-state"

backup="$("$BIN/athena-backup" test)"
[ -d "$backup" ] || fail backup_directory
for file in manifest.txt checksums.sha256 etc-config.tar.gz daed-database.tar.gz web-config.tar.gz runtime-config.tar.gz system-report.txt; do
	[ -f "$backup/$file" ] || fail "missing_$file"
done
"$BIN/athena-backup" --verify "$backup" >/dev/null || fail verify
printf 'corrupt\n' >>"$backup/system-report.txt"
! "$BIN/athena-backup" --verify "$backup" >/dev/null 2>&1 || fail corruption
echo "PASS: backup"
