#!/bin/sh
set -eu
export PROJECT_ROOT="${PROJECT_ROOT:?}"
export ATHENA_LIBDIR="$PROJECT_ROOT/packages/athena-runtime/files/usr/lib/athena"
BIN="$PROJECT_ROOT/packages/athena-runtime/files/usr/bin/athena-iot"

"$BIN" validate "Home-IoT" "safe-pass-1234" 6 >/dev/null
! "$BIN" validate "" "safe-pass-1234" 6 >/dev/null 2>&1
! "$BIN" validate "Home-IoT" "short" 6 >/dev/null 2>&1
! "$BIN" validate "Home-IoT" "safe-pass-1234" 3 >/dev/null 2>&1
grep -q "ieee80211w='0'" "$PROJECT_ROOT/packages/athena-runtime/files/usr/lib/athena/iot.sh"
grep -q "htmode='HT20'" "$PROJECT_ROOT/packages/athena-runtime/files/usr/lib/athena/iot.sh"
grep -q "encryption='psk2+ccmp'" "$PROJECT_ROOT/packages/athena-runtime/files/usr/lib/athena/iot.sh"
grep -q "ieee80211r='0'" "$PROJECT_ROOT/packages/athena-runtime/files/usr/lib/athena/iot.sh"
grep -q "hidden='0'" "$PROJECT_ROOT/packages/athena-runtime/files/usr/lib/athena/iot.sh"
grep -q "isolate='0'" "$PROJECT_ROOT/packages/athena-runtime/files/usr/lib/athena/iot.sh"
printf 'PASS: iot\n'
