#!/usr/bin/env bash
set -euo pipefail

OPENWRT_DIR="${1:?openwrt source directory is required}"
DAEDE_REPO="${DAEDE_REPO:-https://github.com/kenzok8/openwrt-daede.git}"
DAEDE_REF="${DAEDE_REF:-main}"
GEODATA_REPO="${GEODATA_REPO:-https://github.com/Openwrt-Passwall/openwrt-passwall-packages.git}"
GEODATA_REF="${GEODATA_REF:-main}"
VMLINUX_BTF_REPO="${VMLINUX_BTF_REPO:-https://github.com/kenzok8/vmlinux-btf.git}"
VMLINUX_BTF_REF="${VMLINUX_BTF_REF:-main}"

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
clone_ref "$VMLINUX_BTF_REPO" "$VMLINUX_BTF_REF" "$TMP_ROOT/vmlinux-btf"

DAEDE_COMMIT="$(git -C "$TMP_ROOT/openwrt-daede" rev-parse HEAD)"
VMLINUX_BTF_COMMIT="$(git -C "$TMP_ROOT/vmlinux-btf" rev-parse HEAD)"
DAED_VERSION="$(sed -n 's/^PKG_VERSION:=//p' "$TMP_ROOT/openwrt-daede/daed/Makefile" | head -1)"
LUCI_DAEDE_VERSION="$(sed -n 's/^PKG_VERSION:=//p' "$TMP_ROOT/openwrt-daede/luci-app-daede/Makefile" | head -1)"

cd "$OPENWRT_DIR"
mkdir -p package/custom

rm -rf \
    package/custom/dae \
    package/custom/daed \
    package/custom/luci-app-daede \
    package/custom/vmlinux-btf \
    package/feeds/*/dae \
    package/feeds/*/daed \
    package/feeds/*/luci-app-daede \
    package/feeds/*/vmlinux-btf \
    package/feeds/luci/luci-app-dae \
    package/feeds/luci/luci-app-daed 2>/dev/null || true

cp -a "$TMP_ROOT/openwrt-daede/daed" package/custom/
cp -a "$TMP_ROOT/openwrt-daede/luci-app-daede" package/custom/
cp -a "$TMP_ROOT/vmlinux-btf/vmlinux-btf" package/custom/

# Keep DAED's upstream conditional dependency on vmlinux-btf. This build
# selects that backend to keep BTF data outside the 6144 KiB boot kernel.

# This project is DAED-only. Replace the conditional dae/daed dependency with
# a direct daed dependency, while leaving the LuCI source itself unchanged.
python3 - "$OPENWRT_DIR/package/custom/luci-app-daede/Makefile" <<'PY_PATCH_LUCI'
from pathlib import Path
import sys

path = Path(sys.argv[1])
lines = path.read_text(encoding="utf-8").splitlines()
out = []
i = 0
patched = False

while i < len(lines):
    line = lines[i]
    if "DEPENDS:=+luci-base" in line:
        indent = line[: len(line) - len(line.lstrip())]
        out.append(f"{indent}DEPENDS:=+luci-base +daed")
        patched = True

        while line.rstrip().endswith("\\"):
            i += 1
            if i >= len(lines):
                raise SystemExit("unterminated DEPENDS continuation")
            line = lines[i]

        i += 1
        continue

    out.append(line)
    i += 1

if not patched:
    raise SystemExit("luci-app-daede DEPENDS block not found")

path.write_text("\n".join(out) + "\n", encoding="utf-8")
PY_PATCH_LUCI

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
test -f package/custom/vmlinux-btf/Makefile

if ! grep -q 'DAED_USE_VMLINUX_BTF:vmlinux-btf' package/custom/daed/Makefile; then
    echo "::error::DAED detached-BTF dependency is missing."
    exit 1
fi

if ! grep -q 'DEPENDS:=+luci-base +daed' package/custom/luci-app-daede/Makefile; then
    echo "::error::luci-app-daede was not converted to a DAED-only dependency."
    exit 1
fi

stale_packages=(
    package/feeds/luci/luci-app-dae
    package/feeds/luci/luci-app-daed
)

for stale_package in "${stale_packages[@]}"; do
    if [ -e "$stale_package" ]; then
        echo "::error::Stale feed package still exists: $stale_package"
        exit 1
    fi
done

{
    echo "DAEDE_COMMIT=$DAEDE_COMMIT"
    echo "VMLINUX_BTF_COMMIT=$VMLINUX_BTF_COMMIT"
    echo "DAED_VERSION=$DAED_VERSION"
    echo "LUCI_DAEDE_VERSION=$LUCI_DAEDE_VERSION"
    echo "GEODATA_COMMIT=$GEODATA_COMMIT"
} >> "$GITHUB_ENV"

echo "DAED package version: $DAED_VERSION"
echo "vmlinux-btf commit: $VMLINUX_BTF_COMMIT"
echo "luci-app-daede version: $LUCI_DAEDE_VERSION"
