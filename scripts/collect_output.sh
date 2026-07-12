#!/usr/bin/env bash
set -euo pipefail

TOPDIR="${1:?usage: collect_output.sh OPENWRT_TOPDIR OUTPUT_DIR}"
OUTPUT="${2:?usage: collect_output.sh OPENWRT_TOPDIR OUTPUT_DIR}"
TOPDIR="$(cd "$TOPDIR" && pwd)"

rm -rf "$OUTPUT"
mkdir -p "$OUTPUT/firmware" "$OUTPUT/diagnostics"

copy_matches() {
    local dest="$1"
    shift
    local found=0
    while IFS= read -r -d '' file; do
        cp -a "$file" "$dest/"
        found=1
    done < <(find "$TOPDIR" "$@" -print0 2>/dev/null)
    return "$found"
}

# The two files that matter most:
find "$TOPDIR/bin/targets/qualcommax/ipq60xx" -maxdepth 1 -type f \
    \( -name '*jdcloud_re-cs-02*sysupgrade.bin' \
       -o -name '*jdcloud_re-cs-02*initramfs*uImage.itb' \
       -o -name '*jdcloud_re-cs-02*manifest' \
       -o -name 'profiles.json' \
       -o -name 'sha256sums' \) \
    -exec cp -a {} "$OUTPUT/firmware/" \; 2>/dev/null || true

cp -a "$TOPDIR/.config" "$OUTPUT/diagnostics/athena-minimal-final.config" 2>/dev/null || true
"$TOPDIR/scripts/diffconfig.sh" > "$OUTPUT/diagnostics/athena-minimal-diffconfig.txt" 2>/dev/null || true

find "$TOPDIR/build_dir" -type f -name 'jdcloud_re-cs-02-uImage.itb' \
    -exec cp -a {} "$OUTPUT/diagnostics/" \; 2>/dev/null || true

{
    echo "build_time_utc=$(date -u +'%Y-%m-%dT%H:%M:%SZ')"
    echo "source_repo=${SOURCE_REPO:-unknown}"
    echo "source_branch=${SOURCE_BRANCH:-unknown}"
    echo "source_commit_expected=${SOURCE_COMMIT:-unknown}"
    echo "source_commit_actual=$(git -C "$TOPDIR" rev-parse HEAD 2>/dev/null || echo unknown)"
    echo "kernel_slot_limit=6291456"
    echo "btf_mode=detached-vmlinux-btf"
    echo "daede_commit=${DAEDE_COMMIT:-unknown}"
    echo "vmlinux_btf_commit=${VMLINUX_BTF_COMMIT:-unknown}"
    echo "athena_led_commit=${ATHENA_LED_COMMIT:-unknown}"
    echo "golang_commit=${GOLANG_COMMIT:-unknown}"
} > "$OUTPUT/BUILD_INFO.txt"

cat > "$OUTPUT/FLASH_FIRST.txt" <<'EOF'
DO NOT flash the sysupgrade image first.

1. Enter the custom U-Boot web interface.
2. Use its "boot uImage" / initramfs page.
3. Upload the jdcloud_re-cs-02 initramfs-uImage.itb file.
4. Confirm LAN, Wi-Fi, LuCI, front display, detached BTF and DAED packages.
5. Reboot: the old installed firmware should return.
6. Only after the RAM test is stable, flash the sysupgrade.bin without keeping settings.

The HLOS partition is physically 6 MiB. Never enlarge KERNEL_SIZE in source
unless the real HLOS/HLOS_1 partitions and bootloader logic are changed together.
EOF

cp -a "$GITHUB_WORKSPACE/scripts/verify_after_flash.sh" \
    "$OUTPUT/verify-after-flash.sh" 2>/dev/null || true
chmod +x "$OUTPUT/verify-after-flash.sh" 2>/dev/null || true

(
    cd "$OUTPUT"
    find . -type f ! -name SHA256SUMS.txt -print0 |
        sort -z |
        xargs -0 sha256sum > SHA256SUMS.txt
)
