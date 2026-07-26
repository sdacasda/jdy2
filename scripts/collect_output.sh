#!/usr/bin/env bash
set -euo pipefail
TOPDIR="${1:?usage: collect_output.sh OPENWRT_ROOT OUTPUT_ROOT}"
OUTPUT="${2:?usage: collect_output.sh OPENWRT_ROOT OUTPUT_ROOT}"
PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
TARGET="$TOPDIR/bin/targets/qualcommax/ipq60xx"
mkdir -p "$OUTPUT"/{firmware,metadata,diagnostics,tools,docs}
mapfile -t initramfs < <(find "$TARGET" -maxdepth 1 -type f -name '*jdcloud_re-cs-02*initramfs*uImage.itb')
mapfile -t sysupgrade < <(find "$TARGET" -maxdepth 1 -type f -name '*jdcloud_re-cs-02*squashfs-sysupgrade.bin')
[ "${#initramfs[@]}" -eq 1 ] || { echo "Expected one initramfs, found ${#initramfs[@]}" >&2; exit 1; }
[ "${#sysupgrade[@]}" -eq 1 ] || { echo "Expected one sysupgrade, found ${#sysupgrade[@]}" >&2; exit 1; }
cp "${initramfs[0]}" "$OUTPUT/firmware/athena-v19-initramfs-uImage.itb"
cp "${sysupgrade[0]}" "$OUTPUT/firmware/athena-v19-squashfs-sysupgrade.bin"
for f in profiles.json *manifest sha256sums; do
	found="$(find "$TARGET" -maxdepth 1 -type f -name "$f" -print -quit 2>/dev/null || true)"
	[ -z "$found" ] || cp "$found" "$OUTPUT/firmware/"
done
cp "$PROJECT_ROOT/SOURCES.lock.json" "$PROJECT_ROOT/PROJECT.json" "$OUTPUT/metadata/"
cp "$TOPDIR/.config" "$OUTPUT/metadata/effective.config" 2>/dev/null || true
"$TOPDIR/scripts/diffconfig.sh" >"$OUTPUT/metadata/diffconfig" 2>/dev/null || true
[ ! -d "$PROJECT_ROOT/package-registration" ] ||
	cp -a "$PROJECT_ROOT/package-registration" "$OUTPUT/diagnostics/"
cp "$PROJECT_ROOT/scripts/verify_after_flash.sh" "$PROJECT_ROOT/scripts/verify_checksums.sh" "$OUTPUT/tools/"
for f in FLASH.md SETUP.md RECOVERY.md IOT_WIFI.md; do [ ! -f "$PROJECT_ROOT/docs/$f" ] || cp "$PROJECT_ROOT/docs/$f" "$OUTPUT/docs/"; done
printf 'version=19.0.0-rc1\nbuild_time_utc=%s\n' "$(date -u +%FT%TZ)" >"$OUTPUT/metadata/BUILD_INFO.txt"
(cd "$OUTPUT/firmware" && find . -type f ! -name SHA256SUMS -print0 | sort -z | xargs -0 sha256sum >SHA256SUMS)
(cd "$OUTPUT" && find . -type f ! -name SHA256SUMS.txt -print0 | sort -z | xargs -0 sha256sum >SHA256SUMS.txt)
echo "PASS: artifact collected in $OUTPUT"
