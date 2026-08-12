#!/usr/bin/env bash
set -euo pipefail

TOPDIR="${1:?usage: assemble_daed_source.sh OPENWRT_TOPDIR}"
TOPDIR="$(cd "$TOPDIR" && pwd)"
PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
DAEDE_ROOT="$TOPDIR/.package-sources-v19/daede"
PINS="$DAEDE_ROOT/ci/pins.env"
MAKEFILE="$TOPDIR/package/custom/daed/Makefile"
PROVENANCE="$PROJECT_ROOT/daed-source-provenance"

[ -f "$PINS" ] || { echo "locked DAED pins are missing: $PINS" >&2; exit 1; }
[ -f "$MAKEFILE" ] || { echo "locked DAED Makefile is missing: $MAKEFILE" >&2; exit 1; }
[ -f "$DAEDE_ROOT/ci/default.pgo" ] || { echo "locked DAED PGO profile is missing" >&2; exit 1; }

pin() {
	local key="$1" value
	value="$(sed -n "s/^${key}=//p" "$PINS")"
	[ -n "$value" ] || { echo "missing DAED source pin: $key" >&2; exit 1; }
	printf '%s' "$value"
}

DAED_VERSION="$(pin DAED_VERSION)"
DAED_COMMIT="$(pin DAED_COMMIT)"
WING_COMMIT="$(pin WING_COMMIT)"
CORE_COMMIT="$(pin CORE_COMMIT)"
CORE_UPSTREAM_COMMIT="$(pin CORE_UPSTREAM_COMMIT)"
OUTBOUND_COMMIT="$(pin OUTBOUND_COMMIT)"
QUICGO_BASE_COMMIT="$(pin QUICGO_BASE_COMMIT)"
SOURCE_NAME="$(sed -n 's/^PKG_SOURCE:=//p' "$MAKEFILE")"
[ -n "$SOURCE_NAME" ] || { echo "DAED PKG_SOURCE is missing" >&2; exit 1; }

PATCH_HASH="$(sha256sum "$PROJECT_ROOT/scripts/patch_daed_web.py" | cut -d' ' -f1)"
DATABASE_PATCH_HASH="$(sha256sum "$PROJECT_ROOT/scripts/patch_daed_database.py" | cut -d' ' -f1)"
ASSEMBLY_HASH="$(sha256sum "${BASH_SOURCE[0]}" | cut -d' ' -f1)"
CACHE_ID="$(printf '%s\n' \
	"$DAED_VERSION" "$DAED_COMMIT" "$WING_COMMIT" "$CORE_COMMIT" \
	"$CORE_UPSTREAM_COMMIT" "$OUTBOUND_COMMIT" "$QUICGO_BASE_COMMIT" \
	"$PATCH_HASH" "$DATABASE_PATCH_HASH" "$ASSEMBLY_HASH" | sha256sum | cut -c1-16)"
CACHE_DIR="$PROJECT_ROOT/.cache/daed-source/$CACHE_ID"
ARCHIVE="$CACHE_DIR/$SOURCE_NAME"
MANIFEST="$CACHE_DIR/assembly-manifest.json"
BUILD_ROOT="$CACHE_DIR/build"
OUT_NAME="daed-$DAED_VERSION"
OUT="$BUILD_ROOT/$OUT_NAME"

mkdir -p "$CACHE_DIR" "$PROVENANCE"
printf '%s\n' "$CACHE_ID" > "$PROVENANCE/cache-id.txt"
cp "$PINS" "$PROVENANCE/pins.env"

fetch_at() {
	local repository="$1" destination="$2" commit="$3" actual
	git clone --filter=blob:none --no-checkout "$repository" "$destination"
	git -C "$destination" checkout --detach "$commit"
	actual="$(git -C "$destination" rev-parse HEAD)"
	[ "$actual" = "$commit" ] || {
		echo "immutable checkout mismatch: $repository ($actual != $commit)" >&2
		exit 1
	}
}

cache_manifest() {
	python3 "$PROJECT_ROOT/scripts/verify_daed_source_cache.py" \
		--archive "$ARCHIVE" \
		--manifest "$MANIFEST" \
		--cache-id "$CACHE_ID" \
		--pin "DAED_VERSION=$DAED_VERSION" \
		--pin "DAED_COMMIT=$DAED_COMMIT" \
		--pin "WING_COMMIT=$WING_COMMIT" \
		--pin "CORE_COMMIT=$CORE_COMMIT" \
		--pin "CORE_UPSTREAM_COMMIT=$CORE_UPSTREAM_COMMIT" \
		--pin "OUTBOUND_COMMIT=$OUTBOUND_COMMIT" \
		--pin "QUICGO_BASE_COMMIT=$QUICGO_BASE_COMMIT" \
		--pin "WEB_PATCH_SHA256=$PATCH_HASH" \
		--pin "DATABASE_PATCH_SHA256=$DATABASE_PATCH_HASH" \
		--pin "ASSEMBLY_SCRIPT_SHA256=$ASSEMBLY_HASH" \
		"$@"
}

if [ -s "$ARCHIVE" ] && cache_manifest; then
	echo "PASS: restored DAED source cache passed manifest and embedded-Web validation"
else
	echo "DAED source cache is absent or invalid; rebuilding from immutable commits"
	rm -f "$ARCHIVE" "$MANIFEST" "$ARCHIVE.tmp"
	rm -rf "$BUILD_ROOT"
	mkdir -p "$BUILD_ROOT"

	fetch_at https://github.com/daeuniverse/daed "$OUT" "$DAED_COMMIT"
	rm -rf "$OUT/wing"
	fetch_at https://github.com/daeuniverse/dae-wing "$OUT/wing" "$WING_COMMIT"
	rm -rf "$OUT/wing/dae-core"
	fetch_at https://github.com/kenzok8/dae "$OUT/wing/dae-core" "$CORE_COMMIT"
	git -C "$OUT/wing/dae-core" fetch --no-tags \
		https://github.com/daeuniverse/dae "$CORE_UPSTREAM_COMMIT"
	git -C "$OUT/wing/dae-core" -c user.email=ci@local -c user.name=ci \
		merge --no-edit "$CORE_UPSTREAM_COMMIT"
	git -C "$OUT/wing/dae-core" submodule update --init
	fetch_at https://github.com/kenzok8/outbound "$OUT/outbound" "$OUTBOUND_COMMIT"
	fetch_at https://github.com/kenzok8/quic-go "$OUT/quic-go" "$QUICGO_BASE_COMMIT"
	git -C "$OUT/quic-go" -c user.name=ci -c user.email=ci@local \
		am "$DAEDE_ROOT"/ci/patches/quic-go/*.patch
	python3 "$PROJECT_ROOT/scripts/patch_daed_database.py" "$OUT"

	(
		cd "$OUT/wing/dae-core"
		go mod tidy
	)
	(
		cd "$OUT/wing"
		go mod edit -replace github.com/daeuniverse/outbound=../outbound
		go mod edit -replace github.com/daeuniverse/quic-go=../quic-go
		go mod tidy
		cp "$DAEDE_ROOT/ci/default.pgo" default.pgo
	)

	# This must run before pnpm build; patching TypeScript after the prebuilt Web
	# bundle is embedded does not change the shipped DAED frontend.
	python3 "$PROJECT_ROOT/scripts/patch_daed_web.py" "$OUT"
	corepack enable pnpm
	(
		cd "$OUT"
		pnpm install --lockfile-only --ignore-scripts
		pnpm install --frozen-lockfile
		pnpm build --filter daed
	)
	grep -RqsF '/athena-daed/graphql' "$OUT/apps/web/dist" || {
		echo "compiled DAED Web does not contain the same-origin endpoint" >&2
		exit 1
	}
	mkdir -p "$OUT/wing/webrender/web"
	cp -rf "$OUT/apps/web/dist/"* "$OUT/wing/webrender/web/"
	find "$OUT/wing/webrender/web" -name '*.map' -type f -delete
	find "$OUT/wing/webrender/web" -type f -size +4k \
		! -name '*.gz' ! -name '*.woff' ! -name '*.woff2' \
		-exec sh -c 'gzip -n -9 -k "$1"; [ "$(stat -c%s "$1")" -lt "$(stat -c%s "$1.gz")" ] && rm "$1.gz" || rm "$1"' _ {} \;

	find "$OUT" -name .git -type d -prune -exec rm -rf {} +
	find "$OUT" -name node_modules -type d -prune -exec rm -rf {} +
	find "$OUT" -exec touch -h -d '@0' {} +
	(
		cd "$BUILD_ROOT"
		tar --numeric-owner --owner=0 --group=0 --sort=name --mtime='@0' \
			--format=gnu -cf - "$OUT_NAME" | gzip -n -9 > "$ARCHIVE.tmp"
	)
	mv "$ARCHIVE.tmp" "$ARCHIVE"
	rm -rf "$BUILD_ROOT"
	cache_manifest --write
fi

# Always revalidate cache inputs, digest, source patch and the compressed or
# uncompressed embedded Web assets before the archive reaches OpenWrt's dl/.
cache_manifest
cp "$MANIFEST" "$PROVENANCE/assembly-manifest.json"

tar -tzf "$ARCHIVE" > "$PROVENANCE/archive-contents.txt"
grep -qxF "$OUT_NAME/wing/go.mod" "$PROVENANCE/archive-contents.txt" || {
	echo "assembled DAED archive is missing wing/go.mod" >&2
	exit 1
}
grep -qE "^${OUT_NAME}/wing/webrender/web/index\.html(\.gz)?$" \
	"$PROVENANCE/archive-contents.txt" || {
	echo "assembled DAED archive is missing the embedded Web entry" >&2
	exit 1
}
tar -xOzf "$ARCHIVE" "$OUT_NAME/apps/web/src/constants/default.ts" \
	| grep -F '/athena-daed/graphql' >/dev/null || {
	echo "assembled DAED archive does not contain the source endpoint patch" >&2
	exit 1
}

STATIC_WEB_DEST="$TOPDIR/package/custom/luci-app-athena/root/www/athena-daed"
STATIC_WEB_PACKAGE_MANIFEST="$TOPDIR/package/custom/luci-app-athena/root/usr/share/athena/daed-static-web.json"
STATIC_WEB_PROVENANCE="$PROVENANCE/static-web.json"
python3 "$PROJECT_ROOT/scripts/install_daed_web.py" \
	--archive "$ARCHIVE" \
	--destination "$STATIC_WEB_DEST" \
	--provenance "$STATIC_WEB_PACKAGE_MANIFEST"
test -s "$STATIC_WEB_DEST/index.html"
test -s "$STATIC_WEB_PACKAGE_MANIFEST"
cp "$STATIC_WEB_PACKAGE_MANIFEST" "$STATIC_WEB_PROVENANCE"
test -s "$STATIC_WEB_PROVENANCE"

python3 "$PROJECT_ROOT/scripts/install_daed_source.py" \
	--makefile "$MAKEFILE" \
	--archive "$ARCHIVE" \
	--dl-dir "$TOPDIR/dl" \
	--provenance "$PROVENANCE/archive.json"
sha256sum "$ARCHIVE" > "$PROVENANCE/archive.sha256"
echo "PASS: DAED source is locally assembled and pinned ($CACHE_ID)"
