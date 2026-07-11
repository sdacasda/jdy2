#!/usr/bin/env bash
set -uo pipefail

OPENWRT_DIR="${1:?openwrt source directory is required}"
OUTPUT_DIR="${2:?output directory is required}"
BUILD_RESULT="${BUILD_RESULT:-unknown}"
BUILD_MODE="${BUILD_MODE:-unknown}"

mkdir -p "$OUTPUT_DIR"

[ -f "$OPENWRT_DIR/.config" ] && cp -f "$OPENWRT_DIR/.config" "$OUTPUT_DIR/athena-daed-final.config"
[ -f "$GITHUB_WORKSPACE/build.log" ] && cp -f "$GITHUB_WORKSPACE/build.log" "$OUTPUT_DIR/build.log"
cp -f "$GITHUB_WORKSPACE/scripts/verify_after_flash.sh" "$OUTPUT_DIR/verify-after-flash.sh"

TARGET_DIR="$OPENWRT_DIR/bin/targets/qualcommax/ipq60xx"
if [ -d "$TARGET_DIR" ]; then
    find "$TARGET_DIR" -maxdepth 1 -type f \
        \( -name '*jdcloud_re-cs-02*' \
        -o -name '*.manifest' \
        -o -name '*.buildinfo' \
        -o -name '*.json' \
        -o -name 'sha256sums' \) \
        -exec cp -f {} "$OUTPUT_DIR/" \;
fi

SYSUPGRADE_COUNT="$(
    find "$OUTPUT_DIR" -maxdepth 1 -type f \
        -name '*jdcloud_re-cs-02*sysupgrade.bin' | wc -l
)"

{
    echo "result=$BUILD_RESULT"
    echo "build_mode=$BUILD_MODE"
    echo "source_repo=${SOURCE_REPO:-unknown}"
    echo "source_ref=${SOURCE_REF:-unknown}"
    echo "source_commit=${SOURCE_COMMIT:-unknown}"
    echo "target_kernel=${TARGET_KERNEL:-unknown}"
    echo "bpf_headers_kernel=${BPF_HEADERS_KERNEL:-unknown}"
    echo "daede_ref=${DAEDE_REF:-unknown}"
    echo "daede_commit=${DAEDE_COMMIT:-unknown}"
    echo "daed_version=${DAED_VERSION:-unknown}"
    echo "luci_daede_version=${LUCI_DAEDE_VERSION:-unknown}"
    echo "geodata_commit=${GEODATA_COMMIT:-unknown}"
    echo "compile_jobs=${COMPILE_JOBS:-unknown}"
    echo "lan_ip=${LAN_IP:-unknown}"
    echo "sysupgrade_count=$SYSUPGRADE_COUNT"
    echo "generated=$(date -Iseconds)"
} > "$OUTPUT_DIR/BUILD_INFO.txt"

(
    cd "$OUTPUT_DIR"
    sha256sum ./* 2>/dev/null | grep -v 'SHA256SUMS$' > SHA256SUMS || true
)

ls -lh "$OUTPUT_DIR"

if [ "$BUILD_RESULT" = "success" ] && [ "$BUILD_MODE" = "build" ] && [ "$SYSUPGRADE_COUNT" -lt 1 ]; then
    echo "::error::Full build reported success but no RE-CS-02 sysupgrade image was collected."
    exit 1
fi

if [ "$BUILD_MODE" = "validate" ]; then
    echo "Validation mode: firmware image is not expected."
fi
