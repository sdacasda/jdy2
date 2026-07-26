#!/bin/sh

ATHENA_LIBDIR="${ATHENA_LIBDIR:-/usr/lib/athena}"
. "$ATHENA_LIBDIR/common.sh"

athena_sha256sum() {
	if [ -n "${ATHENA_SHA256_CMD:-}" ]; then
		sh "$ATHENA_SHA256_CMD" "$@"
	else
		sha256sum "$@"
	fi
}

athena_backup_archive() {
	output="$1"
	shift
	set -- "$@"
	existing=""
	for relative in "$@"; do
		[ -e "$(athena_root "/$relative")" ] && existing="$existing $relative"
	done
	if [ -n "$existing" ]; then
		# Paths are fixed internal names without whitespace.
		# shellcheck disable=SC2086
		tar -czf "$output" -C "$(athena_root /)" $existing
	else
		tar -czf "$output" -T /dev/null
	fi
}

athena_backup_verify() {
	directory="$1"
	[ -d "$directory" ] && [ -f "$directory/checksums.sha256" ] || return 1
	(cd "$directory" && athena_sha256sum -c checksums.sha256 >/dev/null 2>&1)
}

athena_backup_create() {
	label="${1:-manual}"
	athena_lock backup || athena_die "another backup is running"
	trap 'athena_unlock' EXIT INT TERM
	root="$(athena_root /root/athena-backups)"
	mkdir -p "$root"
	chmod 700 "$root" 2>/dev/null || true
	timestamp="$(date '+%Y%m%d-%H%M%S')"
	final="$root/$timestamp"
	sequence=0
	while [ -e "$final" ]; do
		sequence=$((sequence + 1))
		final="$root/$timestamp-$sequence"
	done
	stage="$final.staging.$$"
	umask 077
	mkdir -p "$stage"

	athena_backup_archive "$stage/etc-config.tar.gz" etc/config
	athena_backup_archive "$stage/daed-database.tar.gz" etc/daed
	athena_backup_archive "$stage/web-config.tar.gz" etc/nginx etc/config/uhttpd etc/config/nginx
	athena_backup_archive "$stage/runtime-config.tar.gz" etc/config/athena var/lib/athena etc/init.d/athena-runtime
	{
		printf 'version=v19\n'
		printf 'created=%s\n' "$(date -u '+%Y-%m-%dT%H:%M:%SZ')"
		printf 'label=%s\n' "$(printf '%s' "$label" | tr -cd 'A-Za-z0-9._-')"
		printf 'root=%s\n' "$ATHENA_ROOT"
	} >"$stage/manifest.txt"
	{
		printf 'device='
		cat "$(athena_root /tmp/sysinfo/board_name)" 2>/dev/null || printf unknown
		printf '\nsetup_state='
		sed -n 's/^STATE=//p' "$(athena_root /var/lib/athena/setup-state)" 2>/dev/null | head -n1
		printf '\n'
	} >"$stage/system-report.txt"
	(cd "$stage" && athena_sha256sum manifest.txt etc-config.tar.gz daed-database.tar.gz web-config.tar.gz runtime-config.tar.gz system-report.txt >checksums.sha256)
	athena_backup_verify "$stage" || {
		rm -rf "$stage"
		athena_die "backup verification failed"
	}
	mv "$stage" "$final"

	retention="$(athena_uci_get athena.main.backup_retention 3)"
	case "$retention" in *[!0-9]*|"") retention=3 ;; esac
	count=0
	for directory in $(find "$root" -mindepth 1 -maxdepth 1 -type d ! -name '*.staging.*' | sort -r); do
		count=$((count + 1))
		if [ "$count" -gt "$retention" ] && athena_backup_verify "$directory"; then
			rm -rf "$directory"
		fi
	done
	athena_unlock
	trap - EXIT INT TERM
	printf '%s\n' "$final"
}

athena_backup_latest() {
	find "$(athena_root /root/athena-backups)" -mindepth 1 -maxdepth 1 -type d 2>/dev/null | sort -r | head -n1
}
