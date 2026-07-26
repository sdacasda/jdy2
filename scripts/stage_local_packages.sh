#!/usr/bin/env bash
set -euo pipefail

TOPDIR="${1:?usage: stage_local_packages.sh OPENWRT_TOPDIR}"
TOPDIR="$(cd "$TOPDIR" && pwd)"
PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
CUSTOM="$TOPDIR/package/custom"

mkdir -p "$CUSTOM"

for package in athena-runtime luci-app-athena; do
	source_dir="$PROJECT_ROOT/packages/$package"
	destination="$CUSTOM/$package"

	test -f "$source_dir/Makefile" || {
		echo "missing local package Makefile: $source_dir/Makefile" >&2
		exit 1
	}

	rm -rf "$destination"
	cp -a "$source_dir" "$destination"

	test -f "$destination/Makefile" || {
		echo "local package staging failed: $destination/Makefile" >&2
		exit 1
	}
	test ! -e "$destination/$package" || {
		echo "nested local package directory detected: $destination/$package" >&2
		exit 1
	}
done

echo "PASS: local Athena packages staged before feed metadata generation"
