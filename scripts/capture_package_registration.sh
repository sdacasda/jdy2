#!/usr/bin/env bash
set -euo pipefail

TOPDIR="${1:?usage: capture_package_registration.sh OPENWRT_ROOT OUTPUT_DIR}"
OUTPUT="${2:?usage: capture_package_registration.sh OPENWRT_ROOT OUTPUT_DIR}"

mkdir -p "$OUTPUT/info"

copy_or_mark_missing() {
	local source="$1"
	local destination="$2"

	if [ -f "$source" ]; then
		cp "$source" "$destination"
	else
		printf 'MISSING: %s\n' "$source" >"${destination}.missing"
	fi
}

copy_or_mark_missing \
	"$TOPDIR/tmp/.packageinfo" \
	"$OUTPUT/actual.packageinfo"
copy_or_mark_missing \
	"$TOPDIR/tmp/.config-package.in" \
	"$OUTPUT/actual.config-package.in"
copy_or_mark_missing \
	"$TOPDIR/.config" \
	"$OUTPUT/effective.config"

if [ -r "$TOPDIR/tmp/.packageinfo" ] &&
	[ -r "$TOPDIR/scripts/package-metadata.pl" ]; then
	if ! perl "$TOPDIR/scripts/package-metadata.pl" config \
		"$TOPDIR/tmp/.packageinfo" \
		>"$OUTPUT/recomputed.config-package.in" \
		2>"$OUTPUT/recompute.stderr"; then
		printf 'package-metadata.pl failed; see recompute.stderr\n' \
			>"$OUTPUT/recomputed.config-package.in.failed"
	fi
else
	printf 'MISSING: package metadata input or generator\n' \
		>"$OUTPUT/recomputed.config-package.in.missing"
fi

if [ -d "$TOPDIR/tmp/info" ]; then
	find "$TOPDIR/tmp/info" -maxdepth 1 -type f \
		\( -name '.files-packageinfo*' \
		-o -name '.overrides-packageinfo*' \
		-o -name '.packageinfo-custom_athena-runtime*' \
		-o -name '.packageinfo-custom_luci-app-athena*' \) \
		-exec cp '{}' "$OUTPUT/info/" \;
fi

config_status() {
	local label="$1"
	local file="$2"
	local symbol="$3"

	if [ ! -r "$file" ]; then
		printf '%s PACKAGE_%s: file-missing\n' "$label" "$symbol"
	elif grep -Eq "^[[:space:]]*config PACKAGE_$symbol$" "$file"; then
		printf '%s PACKAGE_%s: present\n' "$label" "$symbol"
	else
		printf '%s PACKAGE_%s: missing\n' "$label" "$symbol"
	fi
}

package_status() {
	local file="$1"
	local package="$2"

	if [ ! -r "$file" ]; then
		printf 'packageinfo %s: file-missing\n' "$package"
	elif grep -Fqx "Package: $package" "$file"; then
		printf 'packageinfo %s: present\n' "$package"
	else
		printf 'packageinfo %s: missing\n' "$package"
	fi
}

{
	printf 'captured_utc: %s\n' "$(date -u +%FT%TZ)"
	package_status "$OUTPUT/actual.packageinfo" athena-runtime
	package_status "$OUTPUT/actual.packageinfo" luci-app-athena
	config_status actual "$OUTPUT/actual.config-package.in" athena-runtime
	config_status actual "$OUTPUT/actual.config-package.in" luci-app-athena
	config_status recomputed "$OUTPUT/recomputed.config-package.in" athena-runtime
	config_status recomputed "$OUTPUT/recomputed.config-package.in" luci-app-athena
} >"$OUTPUT/registration-summary.txt"

cat "$OUTPUT/registration-summary.txt"
