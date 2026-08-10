#!/usr/bin/env bash
set -euo pipefail
TOPDIR="${1:?usage: collect_output.sh OPENWRT_ROOT OUTPUT_ROOT}"
OUTPUT="${2:?usage: collect_output.sh OPENWRT_ROOT OUTPUT_ROOT}"
INSPECTION="${3:-}"
BUILD_LOG="${4:-}"
PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
TARGET="$TOPDIR/bin/targets/qualcommax/ipq60xx"
mkdir -p "$OUTPUT"/{firmware,metadata,diagnostics,tools,docs}

fail_collection() {
	printf '%s\n' "$1" >"$OUTPUT/diagnostics/ARTIFACT_COLLECTION_ERROR.txt"
	printf '%s\n' "$1" >&2
	exit 1
}

if [ -n "$BUILD_LOG" ] && [ -f "$BUILD_LOG" ]; then
	cp "$BUILD_LOG" "$OUTPUT/diagnostics/build.log"
elif [ -f "$PROJECT_ROOT/build.log" ]; then
	cp "$PROJECT_ROOT/build.log" "$OUTPUT/diagnostics/build.log"
fi

if [ -f "$OUTPUT/diagnostics/build.log" ]; then
	grep -Ei \
		'command not found|fatal error:|(^|[^[:alpha:]])error:|undefined reference|no rule to make target|ERROR: package/.+ failed to build|make(\[[0-9]+\])?: \*\*\*' \
		"$OUTPUT/diagnostics/build.log" |
		tail -n 200 >"$OUTPUT/diagnostics/build-error-summary.txt" || true
fi

if [ -d "$TARGET" ]; then
	(
		find -L "$TARGET" -maxdepth 2 \
			-printf '%y %s %p -> %l\n' 2>&1 || true
	) | sort >"$OUTPUT/diagnostics/target-files.txt"
else
	printf 'Target directory is unavailable: %s\n' "$TARGET" \
		>"$OUTPUT/diagnostics/target-files.txt"
fi

[ ! -d "$PROJECT_ROOT/package-registration" ] ||
	cp -a "$PROJECT_ROOT/package-registration" "$OUTPUT/diagnostics/"

cp "$PROJECT_ROOT/SOURCES.lock.json" "$PROJECT_ROOT/PROJECT.json" \
	"$OUTPUT/metadata/"
cp "$TOPDIR/.config" "$OUTPUT/metadata/effective.config" 2>/dev/null || true
"$TOPDIR/scripts/diffconfig.sh" >"$OUTPUT/metadata/diffconfig" 2>/dev/null || true

read_inspection_paths() {
	local key="$1"
	local python="${ATHENA_PYTHON:-python3}"
	"$python" - "$INSPECTION" "$key" <<'PY'
import json
import sys

report_path, key = sys.argv[1:]
with open(report_path, encoding="utf-8") as stream:
    report = json.load(stream)
for path in report.get(key, []):
    print(path)
PY
}

if [ -n "$INSPECTION" ] && [ -f "$INSPECTION" ]; then
	cp "$INSPECTION" "$OUTPUT/diagnostics/firmware-inspection.json"
	[ ! -f "$(dirname "$INSPECTION")/kernel-size.txt" ] ||
		cp "$(dirname "$INSPECTION")/kernel-size.txt" "$OUTPUT/diagnostics/"
	mapfile -t initramfs < <(read_inspection_paths initramfs | tr -d '\r')
	mapfile -t sysupgrade < <(read_inspection_paths sysupgrade | tr -d '\r')
else
	mapfile -t initramfs < <(
		find -L "$TARGET" -maxdepth 1 -type f \
			-name '*jdcloud_re-cs-02*initramfs*uImage.itb'
	)
	mapfile -t sysupgrade < <(
		find -L "$TARGET" -maxdepth 1 -type f \
			-name '*jdcloud_re-cs-02*squashfs-sysupgrade.bin'
	)
fi

[ "${#initramfs[@]}" -eq 1 ] ||
	fail_collection "Expected one initramfs, found ${#initramfs[@]}"
[ "${#sysupgrade[@]}" -eq 1 ] ||
	fail_collection "Expected one sysupgrade, found ${#sysupgrade[@]}"
[ -f "${initramfs[0]}" ] ||
	fail_collection "Validated initramfs is unavailable: ${initramfs[0]}"
[ -f "${sysupgrade[0]}" ] ||
	fail_collection "Validated sysupgrade is unavailable: ${sysupgrade[0]}"

cp "${initramfs[0]}" "$OUTPUT/firmware/athena-v19-initramfs-uImage.itb"
cp "${sysupgrade[0]}" "$OUTPUT/firmware/athena-v19-squashfs-sysupgrade.bin"
for f in profiles.json *manifest; do
	found="$(find "$TARGET" -maxdepth 1 -type f -name "$f" -print -quit 2>/dev/null || true)"
	[ -z "$found" ] || cp "$found" "$OUTPUT/firmware/"
done
upstream_sums="$(
	find "$TARGET" -maxdepth 1 -type f -name sha256sums -print -quit \
		2>/dev/null || true
)"
[ -z "$upstream_sums" ] ||
	cp "$upstream_sums" "$OUTPUT/firmware/UPSTREAM_SHA256SUMS"
cp "$PROJECT_ROOT/scripts/verify_after_flash.sh" "$PROJECT_ROOT/scripts/verify_checksums.sh" "$OUTPUT/tools/"
for f in FLASH.md SETUP.md RECOVERY.md IOT_WIFI.md WEB_RECOVERY.md; do [ ! -f "$PROJECT_ROOT/docs/$f" ] || cp "$PROJECT_ROOT/docs/$f" "$OUTPUT/docs/"; done
printf 'version=19.0.0-rc1\nbuild_time_utc=%s\n' "$(date -u +%FT%TZ)" >"$OUTPUT/metadata/BUILD_INFO.txt"
(cd "$OUTPUT/firmware" && find . -type f ! -name SHA256SUMS -print0 | sort -z | xargs -0 sha256sum >SHA256SUMS)
(cd "$OUTPUT" && find . -type f ! -name SHA256SUMS.txt -print0 | sort -z | xargs -0 sha256sum >SHA256SUMS.txt)
echo "PASS: artifact collected in $OUTPUT"
