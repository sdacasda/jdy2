#!/usr/bin/env bash
set -euo pipefail

TOPDIR="${1:?usage: collect_output.sh OPENWRT_TOPDIR OUTPUT_DIR}"
OUTPUT="${2:?usage: collect_output.sh OPENWRT_TOPDIR OUTPUT_DIR}"

rm -rf "$OUTPUT"
mkdir -p "$OUTPUT"

TARGET="$TOPDIR/bin/targets/qualcommax/ipq60xx"
IMAGE="$(
    find "$TARGET" -maxdepth 1 -type f \
        -name '*jdcloud_re-cs-02*initramfs*uImage.itb' \
        -print -quit 2>/dev/null || true
)"

if [[ -z "$IMAGE" || ! -f "$IMAGE" ]]; then
    echo "::error::No RE-CS-02 initramfs FIT image was generated."
    exit 1
fi

cp -a "$IMAGE" "$OUTPUT/"
cp -a "$TOPDIR/.config" "$OUTPUT/athena-ram-diagnostic-final.config"

cat > "$OUTPUT/README-FIRST.txt" <<'EOF'
THIS ARTIFACT CONTAINS A RAM-ONLY DIAGNOSTIC IMAGE.

Use only the file whose name contains:
  jdcloud_re-cs-02
  initramfs
  uImage.itb

Open the custom U-Boot Web page /uimage.html and choose "启动 uImage".

The artifact intentionally contains no sysupgrade.bin, factory.bin or IMG file.
It cannot be used for a persistent firmware upgrade.

Expected test:
  1. Connect the PC directly by Ethernet.
  2. PC static address: 192.168.1.2 / 255.255.255.0.
  3. Boot the initramfs from U-Boot.
  4. Wait up to 4 minutes.
  5. Ping 192.168.1.1 and open http://192.168.1.1.
  6. Try every physical Ethernet port.

If this tiny baseline still has no network, stop custom-firmware testing.
Without a serial console there is no safe way to identify an early boot failure.
EOF

{
    echo "source_commit=$(git -C "$TOPDIR" rev-parse HEAD)"
    echo "image_name=$(basename "$IMAGE")"
    echo "image_bytes=$(stat -c '%s' "$IMAGE")"
    echo "sha256=$(sha256sum "$IMAGE" | awk '{print $1}')"
} > "$OUTPUT/BUILD_INFO.txt"

(
    cd "$OUTPUT"
    sha256sum ./* > SHA256SUMS.txt
)
