#!/usr/bin/env bash
set -euo pipefail

OPENWRT_DIR="${1:?openwrt source directory is required}"
DAEDE_REPO="${DAEDE_REPO:-https://github.com/kenzok8/openwrt-daede.git}"
DAEDE_REF="${DAEDE_REF:-main}"
GEODATA_REPO="${GEODATA_REPO:-https://github.com/Openwrt-Passwall/openwrt-passwall-packages.git}"
GEODATA_REF="${GEODATA_REF:-main}"

TMP_ROOT="$(mktemp -d)"
trap 'rm -rf "$TMP_ROOT"' EXIT

clone_ref() {
    local repo="$1"
    local ref="$2"
    local dest="$3"

    git init -q "$dest"
    git -C "$dest" remote add origin "$repo"
    git -C "$dest" fetch -q --depth=1 origin "$ref"
    git -C "$dest" checkout -q --detach FETCH_HEAD
}

clone_ref "$DAEDE_REPO" "$DAEDE_REF" "$TMP_ROOT/openwrt-daede"

DAEDE_COMMIT="$(git -C "$TMP_ROOT/openwrt-daede" rev-parse HEAD)"
DAED_VERSION="$(sed -n 's/^PKG_VERSION:=//p' "$TMP_ROOT/openwrt-daede/daed/Makefile" | head -1)"
LUCI_DAEDE_VERSION="$(sed -n 's/^PKG_VERSION:=//p' "$TMP_ROOT/openwrt-daede/luci-app-daede/Makefile" | head -1)"

cd "$OPENWRT_DIR"
mkdir -p package/custom

rm -rf \
    package/custom/dae \
    package/custom/daed \
    package/custom/luci-app-daede \
    package/feeds/*/dae \
    package/feeds/*/daed \
    package/feeds/*/luci-app-daede 2>/dev/null || true

cp -a "$TMP_ROOT/openwrt-daede/daed" package/custom/
cp -a "$TMP_ROOT/openwrt-daede/luci-app-daede" package/custom/

if ! grep -Rqs "define Package/v2ray-geoip" package feeds 2>/dev/null || \
   ! grep -Rqs "define Package/v2ray-geosite" package feeds 2>/dev/null; then
    clone_ref "$GEODATA_REPO" "$GEODATA_REF" "$TMP_ROOT/passwall-packages"
    test -d "$TMP_ROOT/passwall-packages/v2ray-geodata"
    rm -rf package/custom/v2ray-geodata package/feeds/*/v2ray-geodata 2>/dev/null || true
    cp -a "$TMP_ROOT/passwall-packages/v2ray-geodata" package/custom/
    GEODATA_COMMIT="$(git -C "$TMP_ROOT/passwall-packages" rev-parse HEAD)"
else
    GEODATA_COMMIT="source-feed"
fi

test -f package/custom/daed/Makefile
test -f package/custom/luci-app-daede/Makefile

{
    echo "DAEDE_COMMIT=$DAEDE_COMMIT"
    echo "DAED_VERSION=$DAED_VERSION"
    echo "LUCI_DAEDE_VERSION=$LUCI_DAEDE_VERSION"
    echo "GEODATA_COMMIT=$GEODATA_COMMIT"
} >> "$GITHUB_ENV"

echo "DAED package version: $DAED_VERSION"
echo "luci-app-daede version: $LUCI_DAEDE_VERSION"
