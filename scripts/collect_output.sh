#!/usr/bin/env bash
set -euo pipefail
TOPDIR="${1:?usage: collect_output.sh OPENWRT_TOPDIR OUTPUT_DIR}"
OUTPUT="${2:?usage: collect_output.sh OPENWRT_TOPDIR OUTPUT_DIR}"
TARGET="$TOPDIR/bin/targets/qualcommax/ipq60xx"
rm -rf "$OUTPUT"
mkdir -p "$OUTPUT/firmware" "$OUTPUT/diagnostics"

INITRAMFS="$(find "$TARGET" -maxdepth 1 -type f -name '*jdcloud_re-cs-02*initramfs*uImage.itb' -print -quit 2>/dev/null || true)"
SYSUPGRADE="$(find "$TARGET" -maxdepth 1 -type f -name '*jdcloud_re-cs-02*squashfs-sysupgrade.bin' -print -quit 2>/dev/null || true)"

if [[ -n "$INITRAMFS" && -f "$INITRAMFS" ]]; then cp -a "$INITRAMFS" "$OUTPUT/firmware/"; else echo "No initramfs generated" > "$OUTPUT/diagnostics/NO_INITRAMFS.txt"; fi
if [[ -n "$SYSUPGRADE" && -f "$SYSUPGRADE" ]]; then cp -a "$SYSUPGRADE" "$OUTPUT/firmware/"; else echo "No sysupgrade generated" > "$OUTPUT/diagnostics/NO_SYSUPGRADE.txt"; fi

for file in "$TARGET"/sha256sums "$TARGET"/profiles.json "$TARGET"/*manifest; do
  [ -f "$file" ] && cp -a "$file" "$OUTPUT/firmware/" || true
done
cp -a "$TOPDIR/.config" "$OUTPUT/diagnostics/athena-final-candidate.config" 2>/dev/null || true
"$TOPDIR/scripts/diffconfig.sh" > "$OUTPUT/diagnostics/athena-final-candidate.diffconfig" 2>/dev/null || true
find "$TOPDIR/build_dir" -type f -name 'jdcloud_re-cs-02-uImage.itb' -exec cp -a {} "$OUTPUT/diagnostics/" \; 2>/dev/null || true

cat > "$OUTPUT/TEST_FIRST.txt" <<'TXT'
ONE BUILD, TWO IMAGES.

FIRST TEST ONLY:
  *jdcloud_re-cs-02*initramfs*uImage.itb

Use U-Boot /uimage.html. Do not flash sysupgrade first.
Open http://192.168.1.1/diag.html and SSH root@192.168.1.1.
Run: athena-feature-check
Wake-on-LAN is available in LuCI and with etherwake.

The same Artifact contains sysupgrade.bin, so no second cloud build is needed.
Use it only after the full-feature RAM image remains stable.
TXT

{
  echo "build_time_utc=$(date -u +'%Y-%m-%dT%H:%M:%SZ')"
  echo "source_commit=$(git -C "$TOPDIR" rev-parse HEAD 2>/dev/null || echo unknown)"
  echo "kernel_slot_limit=6291456"
  echo "daede_ref=${DAEDE_REF:-unknown}"
  echo "daede_commit=${DAEDE_COMMIT:-unknown}"
  echo "vmlinux_btf_commit=${VMLINUX_BTF_COMMIT:-unknown}"
  echo "athena_led_commit=${ATHENA_LED_COMMIT:-unknown}"
  echo "golang_commit=${GOLANG_COMMIT:-unknown}"
  [[ -z "$INITRAMFS" ]] || echo "initramfs_bytes=$(stat -c '%s' "$INITRAMFS")"
  [[ -z "$SYSUPGRADE" ]] || echo "sysupgrade_bytes=$(stat -c '%s' "$SYSUPGRADE")"
} > "$OUTPUT/BUILD_INFO.txt"

(cd "$OUTPUT" && find . -type f ! -name SHA256SUMS.txt -print0 | sort -z | xargs -0 sha256sum > SHA256SUMS.txt)
