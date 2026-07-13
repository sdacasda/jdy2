#!/bin/sh
set -u
fail=0
ok(){ printf '[OK] %s\n' "$1"; }
bad(){ printf '[FAIL] %s\n' "$1"; fail=1; }

board="$(ubus call system board 2>/dev/null)"
echo "$board" | grep -q '"board_name": "jdcloud,re-cs-02"' && ok "board is jdcloud,re-cs-02" || bad "unexpected board"
case "$(uname -r)" in 6.12.*) ok "kernel is 6.12: $(uname -r)" ;; *) bad "unexpected kernel: $(uname -r)" ;; esac
command -v athena-feature-check >/dev/null 2>&1 && athena-feature-check || bad "athena-feature-check failed or missing"
if [ -e /dev/mmcblk0p16 ]; then
  hlos_bytes="$(blockdev --getsize64 /dev/mmcblk0p16 2>/dev/null || echo unknown)"
  [ "$hlos_bytes" = "6291456" ] && ok "HLOS remains 6 MiB" || bad "unexpected HLOS size: $hlos_bytes"
fi
exit "$fail"
