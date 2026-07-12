#!/usr/bin/env bash
set -euo pipefail

TOPDIR="${1:?usage: prepare_packages.sh OPENWRT_TOPDIR}"
TOPDIR="$(cd "$TOPDIR" && pwd)"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CUSTOM="$TOPDIR/package/custom"
WORK="$TOPDIR/.package-sources"

DAEDE_REPO="${DAEDE_REPO:-https://github.com/kenzok8/openwrt-daede.git}"
DAEDE_REF="${DAEDE_REF:-main}"
VMLINUX_BTF_REPO="${VMLINUX_BTF_REPO:-https://github.com/kenzok8/vmlinux-btf.git}"
VMLINUX_BTF_REF="${VMLINUX_BTF_REF:-main}"
ATHENA_LED_REPO="${ATHENA_LED_REPO:-https://github.com/NONGFAH/luci-app-athena-led.git}"
ATHENA_LED_REF="${ATHENA_LED_REF:-main}"
GOLANG_REPO="${GOLANG_REPO:-https://github.com/sbwml/packages_lang_golang.git}"
GOLANG_REF="${GOLANG_REF:-26.x}"

rm -rf "$CUSTOM" "$WORK"
mkdir -p "$CUSTOM" "$WORK"

clone_ref() {
    local repo="$1"
    local ref="$2"
    local dest="$3"

    git clone --filter=blob:none --no-checkout "$repo" "$dest"
    git -C "$dest" fetch --depth=1 origin "$ref"
    git -C "$dest" checkout --detach FETCH_HEAD
}

record_commit() {
    local name="$1"
    local repo_dir="$2"
    local commit
    commit="$(git -C "$repo_dir" rev-parse HEAD)"
    printf '%s=%s\n' "$name" "$commit"
    if [[ -n "${GITHUB_ENV:-}" ]]; then
        printf '%s=%s\n' "$name" "$commit" >> "$GITHUB_ENV"
    fi
}

echo "Preparing DAED packages..."
clone_ref "$DAEDE_REPO" "$DAEDE_REF" "$WORK/openwrt-daede"
cp -a "$WORK/openwrt-daede/daed" "$CUSTOM/daed"
cp -a "$WORK/openwrt-daede/luci-app-daede" "$CUSTOM/luci-app-daede"

# LiBwrt's defconfig drops the optional DAED_USE_* package-choice symbol.
# This appliance always uses detached BTF, so make vmlinux-btf a direct,
# unconditional dependency and remove the unused package choice.
python3 "$SCRIPT_DIR/patch_daed_btf.py" "$CUSTOM/daed/Makefile"
grep -Fq '+vmlinux-btf' "$CUSTOM/daed/Makefile"
if grep -q 'DAED_USE_' "$CUSTOM/daed/Makefile"; then
    echo "::error::DAED BTF choice symbols remain after patching."
    exit 1
fi

record_commit DAEDE_COMMIT "$WORK/openwrt-daede"

echo "Preparing detached BTF package..."
clone_ref "$VMLINUX_BTF_REPO" "$VMLINUX_BTF_REF" "$WORK/vmlinux-btf"
cp -a "$WORK/vmlinux-btf/vmlinux-btf" "$CUSTOM/vmlinux-btf"
record_commit VMLINUX_BTF_COMMIT "$WORK/vmlinux-btf"

echo "Preparing Athena display package..."
clone_ref "$ATHENA_LED_REPO" "$ATHENA_LED_REF" "$WORK/athena-led"
cp -a "$WORK/athena-led" "$CUSTOM/luci-app-athena-led"
chmod +x \
    "$CUSTOM/luci-app-athena-led/root/usr/sbin/athena-led" \
    "$CUSTOM/luci-app-athena-led/root/etc/init.d/athena_led"
record_commit ATHENA_LED_COMMIT "$WORK/athena-led"

echo "Replacing the Go feed with the Go 1.26-compatible branch..."
rm -rf "$TOPDIR/feeds/packages/lang/golang"
clone_ref "$GOLANG_REPO" "$GOLANG_REF" "$TOPDIR/feeds/packages/lang/golang"
record_commit GOLANG_COMMIT "$TOPDIR/feeds/packages/lang/golang"

has_geodata_packages() {
    grep -RqsE 'define Package/(v2ray-geoip|v2ray-geosite)' \
        "$TOPDIR/feeds/packages" "$CUSTOM" 2>/dev/null
}

if ! has_geodata_packages; then
    echo "v2ray geodata packages were not found; importing the package definition."
    PASSWALL_PACKAGES_REPO="${PASSWALL_PACKAGES_REPO:-https://github.com/xiaorouji/openwrt-passwall-packages.git}"
    PASSWALL_PACKAGES_REF="${PASSWALL_PACKAGES_REF:-main}"
    clone_ref "$PASSWALL_PACKAGES_REPO" "$PASSWALL_PACKAGES_REF" "$WORK/passwall-packages"

    geodata_dir="$(
        find "$WORK/passwall-packages" -type f -name Makefile \
            -exec grep -lE 'define Package/(v2ray-geoip|v2ray-geosite)' {} + |
            head -n 1 |
            xargs -r dirname
    )"

    if [[ -z "$geodata_dir" ]]; then
        echo "::error::Unable to locate v2ray geodata package definitions."
        exit 1
    fi

    cp -a "$geodata_dir" "$CUSTOM/v2ray-geodata"
    record_commit PASSWALL_PACKAGES_COMMIT "$WORK/passwall-packages"
fi

# Guard against stale duplicate package definitions from prior experiments.
find "$TOPDIR/package" -mindepth 1 -maxdepth 3 -type d \
    \( -name daed -o -name luci-app-daede -o -name vmlinux-btf -o -name luci-app-athena-led \) \
    ! -path "$CUSTOM/*" -prune -exec rm -rf {} + 2>/dev/null || true

echo "Custom package preparation completed."
