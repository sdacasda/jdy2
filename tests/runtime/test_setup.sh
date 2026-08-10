#!/bin/sh
set -eu
ROOT="$(mktemp -d)"; trap 'rm -rf "$ROOT"' EXIT
mkdir -p "$ROOT/etc/config"
printf "config athena 'main'\n" >"$ROOT/etc/config/athena"
export ATHENA_ROOT="$ROOT"
export ATHENA_LIBDIR="${PROJECT_ROOT:?}/packages/athena-runtime/files/usr/lib/athena"
BIN="$PROJECT_ROOT/packages/athena-runtime/files/usr/bin/athena-setup"
before="$(wc -c <"$ROOT/etc/config/athena")"
"$BIN" --check >/dev/null
[ "$before" = "$(wc -c <"$ROOT/etc/config/athena")" ]
! "$BIN" --bad >/dev/null 2>&1
grep -q 'awaiting_import' "$BIN"
! grep -q 'wing.db.*sqlite\\|sqlite.*wing.db' "$BIN"
echo "PASS: setup"
