#!/usr/bin/env bash
set -euo pipefail
TOPDIR="${1:?usage: prepare_packages.sh OPENWRT_TOPDIR}"
TOPDIR="$(cd "$TOPDIR" && pwd)"
PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
LOCK="$PROJECT_ROOT/SOURCES.lock.json"
CUSTOM="$TOPDIR/package/custom"
WORK="$TOPDIR/.package-sources-v19"
mkdir -p "$CUSTOM" "$WORK"

lock_value() {
	python3 - "$LOCK" "$1" "$2" <<'PY'
import json,sys
print(json.load(open(sys.argv[1], encoding="utf-8"))[sys.argv[2]][sys.argv[3]])
PY
}

checkout_locked() {
	name="$1"; dest="$2"
	repo="$(lock_value "$name" repository)"
	commit="$(lock_value "$name" commit)"
	rm -rf "$dest"
	git init -q "$dest"
	git -C "$dest" remote add origin "$repo"
	git -C "$dest" fetch -q --depth=1 origin "$commit"
	git -C "$dest" checkout -q --detach FETCH_HEAD
	actual="$(git -C "$dest" rev-parse HEAD)"
	[ "$actual" = "$commit" ] || { echo "locked checkout mismatch: $name" >&2; exit 1; }
	printf '%s=%s\n' "${name^^}_COMMIT" "$actual"
}

checkout_locked daede "$WORK/daede"
cp -a "$WORK/daede/daed" "$CUSTOM/daed"
cp -a "$WORK/daede/luci-app-daede" "$CUSTOM/luci-app-daede"
python3 "$PROJECT_ROOT/scripts/patch_daed_btf.py" "$CUSTOM/daed/Makefile"

checkout_locked vmlinux_btf "$WORK/vmlinux-btf"
cp -a "$WORK/vmlinux-btf/vmlinux-btf" "$CUSTOM/vmlinux-btf"

checkout_locked athena_led "$WORK/athena-led"
cp -a "$WORK/athena-led" "$CUSTOM/luci-app-athena-led"

checkout_locked argon "$WORK/argon"
cp -a "$WORK/argon" "$CUSTOM/luci-theme-argon"
checkout_locked argon_config "$WORK/argon-config"
cp -a "$WORK/argon-config" "$CUSTOM/luci-app-argon-config"

rm -rf "$TOPDIR/feeds/packages/lang/golang"
checkout_locked golang "$TOPDIR/feeds/packages/lang/golang"

if ! grep -RqsE 'define Package/(v2ray-geoip|v2ray-geosite)' "$TOPDIR/feeds/packages" "$CUSTOM" 2>/dev/null; then
	checkout_locked geodata "$WORK/geodata"
	geodata_makefile="$(grep -RlE 'define Package/(v2ray-geoip|v2ray-geosite)' "$WORK/geodata" --include Makefile | head -n1)"
	[ -n "$geodata_makefile" ] || { echo "locked geodata package layout not recognized" >&2; exit 1; }
	cp -a "$(dirname "$geodata_makefile")" "$CUSTOM/v2ray-geodata"
fi

for package in athena-runtime luci-app-athena; do
	[ -f "$CUSTOM/$package/Makefile" ] || {
		echo "local package was not staged before feeds: $package" >&2
		exit 1
	}
done
echo "PASS: all v19 packages imported from immutable commits"
