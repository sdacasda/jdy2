#!/usr/bin/env bash
set -euo pipefail

TOPDIR="${1:?usage: remove_feed_conflicts.sh OPENWRT_TOPDIR}"
TOPDIR="$(cd "$TOPDIR" && pwd)"

case "$TOPDIR" in
	""|/)
		echo "refusing unsafe OpenWrt root: $TOPDIR" >&2
		exit 1
		;;
esac

remove_exact_path() {
	local relative="$1"
	local target="$TOPDIR/$relative"

	case "$target" in
		"$TOPDIR"/*) ;;
		*)
			echo "refusing path outside OpenWrt root: $target" >&2
			exit 1
			;;
	esac

	rm -rf -- "$target"
}

# LiBwrt's packages feed also defines "daed". If it remains visible while
# package metadata is generated, it wins over package/custom/daed and silently
# replaces the immutable kenzok8 build with the incompatible feed release.
remove_exact_path "feeds/packages/net/daed"
remove_exact_path "package/feeds/packages/daed"

echo "PASS: conflicting feed daed package removed"
