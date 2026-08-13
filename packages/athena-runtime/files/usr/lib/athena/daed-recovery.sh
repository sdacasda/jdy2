#!/bin/sh
# Shared DAED credential recovery. Resetpass output is never logged or persisted.

[ -n "${ATHENA_ROOT+x}" ] || ATHENA_ROOT=/
if ! command -v athena_root >/dev/null 2>&1; then
	. "${ATHENA_LIBDIR:-/usr/lib/athena}/common.sh"
fi

athena_daed_recovery_json_error() {
	if [ -n "${2:-}" ]; then
		printf '{"ok":false,"error":"%s","backup":"%s"}\n' "$(athena_json_escape "$1")" "$(athena_json_escape "$2")"
	else
		printf '{"ok":false,"error":"%s"}\n' "$(athena_json_escape "$1")"
	fi
}

athena_daed_recovery_active() {
	"${ATHENA_DAED_INIT:-/etc/init.d/daed}" running >/dev/null 2>&1 ||
		pidof daed >/dev/null 2>&1 || athena_daed_graphql_reachable
}

athena_daed_recovery_wait_stopped() {
	athena_daed_recovery_wait=0
	while [ "$athena_daed_recovery_wait" -lt 5 ]; do
		! pidof daed >/dev/null 2>&1 && ! athena_daed_graphql_reachable && return 0
		sleep 1
		athena_daed_recovery_wait=$((athena_daed_recovery_wait + 1))
	done
	return 1
}

athena_daed_recovery_wait_ready() {
	athena_daed_recovery_wait=0
	while [ "$athena_daed_recovery_wait" -lt 5 ]; do
		pidof daed >/dev/null 2>&1 && athena_daed_graphql_reachable && return 0
		sleep 1
		athena_daed_recovery_wait=$((athena_daed_recovery_wait + 1))
	done
	return 1
}

athena_daed_recovery_validate_database() {
	athena_daed_recovery_validation="$(sqlite3 "$(athena_root /etc/daed/wing.db)" \
		'PRAGMA quick_check; SELECT count(*) FROM users;' 2>/dev/null)" || return 1
	[ "$(printf '%s\n' "$athena_daed_recovery_validation" | sed -n '1p')" = ok ] || return 1
	athena_daed_recovery_user_count="$(printf '%s\n' "$athena_daed_recovery_validation" | sed -n '2p')"
	case "$athena_daed_recovery_user_count" in ''|0|*[!0-9]*) return 1 ;; esac
	[ "$(printf '%s\n' "$athena_daed_recovery_validation" | wc -l | tr -d ' ')" = 2 ]
}

athena_daed_recovery_backup() {
	athena_daed_recovery_db="$(athena_root /etc/daed/wing.db)"
	athena_daed_recovery_root="$(athena_root /root/athena-backups)"
	[ -f "$athena_daed_recovery_db" ] || return 1
	mkdir -p "$athena_daed_recovery_root" || return 1
	athena_daed_recovery_stamp="$(date '+%Y%m%dT%H%M%S' 2>/dev/null || date '+%s')"
	athena_daed_recovery_n=0
	while :; do
		athena_daed_recovery_backup_path="$athena_daed_recovery_root/daed-recovery-$athena_daed_recovery_stamp-$athena_daed_recovery_n"
		mkdir "$athena_daed_recovery_backup_path" 2>/dev/null && break
		athena_daed_recovery_n=$((athena_daed_recovery_n + 1))
		[ "$athena_daed_recovery_n" -lt 100 ] || return 1
	done
	chmod 700 "$athena_daed_recovery_backup_path" || return 1
	for athena_daed_recovery_file in wing.db wing.db-wal wing.db-shm wing.db-journal; do
		athena_daed_recovery_source="$(athena_root "/etc/daed/$athena_daed_recovery_file")"
		if [ "$athena_daed_recovery_file" = wing.db ] || [ -f "$athena_daed_recovery_source" ]; then
			cp "$athena_daed_recovery_source" "$athena_daed_recovery_backup_path/$athena_daed_recovery_file" || return 1
			chmod 600 "$athena_daed_recovery_backup_path/$athena_daed_recovery_file" || return 1
		fi
	done
	{
		printf '%s\n' 'Athena DAED password recovery backup'
		printf 'created=%s\n' "$athena_daed_recovery_stamp"
		printf '%s\n' 'files=wing.db wing.db-wal wing.db-shm wing.db-journal (when present)'
	} >"$athena_daed_recovery_backup_path/manifest.txt" || return 1
	chmod 600 "$athena_daed_recovery_backup_path/manifest.txt" || return 1
	(
		cd "$athena_daed_recovery_backup_path" || exit 1
		for athena_daed_recovery_file in manifest.txt wing.db wing.db-wal wing.db-shm wing.db-journal; do
			[ ! -f "$athena_daed_recovery_file" ] || sha256sum "$athena_daed_recovery_file" || exit 1
		done >checksums.sha256
	) && chmod 600 "$athena_daed_recovery_backup_path/checksums.sha256" &&
	(
		cd "$athena_daed_recovery_backup_path" || exit 1
		sha256sum -c checksums.sha256 >/dev/null
	)
}

athena_daed_recovery_restore_backup() {
	[ -n "$athena_daed_recovery_backup_path" ] || return 1
	(
		cd "$athena_daed_recovery_backup_path" || exit 1
		sha256sum -c checksums.sha256 >/dev/null
	) || return 1
	athena_daed_recovery_restore_root="$(athena_root /etc/daed)"
	for athena_daed_recovery_file in wing.db wing.db-wal wing.db-shm wing.db-journal; do
		athena_daed_recovery_source="$athena_daed_recovery_backup_path/$athena_daed_recovery_file"
		athena_daed_recovery_target="$athena_daed_recovery_restore_root/$athena_daed_recovery_file"
		athena_daed_recovery_tmp="$athena_daed_recovery_restore_root/.athena-daed-restore-$$-$athena_daed_recovery_file"
		if [ -f "$athena_daed_recovery_source" ]; then
			cp "$athena_daed_recovery_source" "$athena_daed_recovery_tmp" || return 1
			chmod 600 "$athena_daed_recovery_tmp" || { rm -f "$athena_daed_recovery_tmp"; return 1; }
			athena_daed_recovery_source_hash="$(sha256sum "$athena_daed_recovery_source" | awk '{print $1}')" || return 1
			athena_daed_recovery_tmp_hash="$(sha256sum "$athena_daed_recovery_tmp" | awk '{print $1}')" || return 1
			[ "$athena_daed_recovery_source_hash" = "$athena_daed_recovery_tmp_hash" ] || { rm -f "$athena_daed_recovery_tmp"; return 1; }
			mv -f "$athena_daed_recovery_tmp" "$athena_daed_recovery_target" || return 1
		elif [ "$athena_daed_recovery_file" != wing.db ]; then
			rm -f "$athena_daed_recovery_target" || return 1
		else
			return 1
		fi
	done
	athena_daed_recovery_validate_database
}

athena_daed_recovery_parse_output() {
	athena_daed_recovery_remaining=$1
	athena_daed_recovery_count=0
	athena_daed_recovery_username=""
	athena_daed_recovery_password=""
	while [ -n "$athena_daed_recovery_remaining" ]; do
		case "$athena_daed_recovery_remaining" in
		*'
'*) athena_daed_recovery_line=${athena_daed_recovery_remaining%%'
'*}; athena_daed_recovery_remaining=${athena_daed_recovery_remaining#*'
'} ;;
		*) athena_daed_recovery_line=$athena_daed_recovery_remaining; athena_daed_recovery_remaining="" ;;
		esac
		case "$athena_daed_recovery_line" in
		'Username: '*', Password: '*) ;;
		*) return 1 ;;
		esac
		athena_daed_recovery_value=${athena_daed_recovery_line#Username: }
		athena_daed_recovery_next_username=${athena_daed_recovery_value%%, Password: *}
		athena_daed_recovery_next_password=${athena_daed_recovery_value#*, Password: }
		[ -n "$athena_daed_recovery_next_username" ] && [ -n "$athena_daed_recovery_next_password" ] || return 1
		# The pinned contract is eight characters; do not invent a username charset.
		[ "${athena_daed_recovery_next_password#????????}" = "" ] && [ "${athena_daed_recovery_next_password%????????}" = "" ] || return 1
		athena_daed_recovery_count=$((athena_daed_recovery_count + 1))
		[ "$athena_daed_recovery_count" -eq 1 ] || return 1
		athena_daed_recovery_username=$athena_daed_recovery_next_username
		athena_daed_recovery_password=$athena_daed_recovery_next_password
	done
	[ "$athena_daed_recovery_count" -eq 1 ]
}

athena_daed_reset_password() {
	[ "${1:-}" = 'RESET DAED PASSWORD' ] || { athena_daed_recovery_json_error 'confirmation phrase is required'; exit 1; }
	umask 077
	athena_daed_recovery_locked=0 athena_daed_recovery_was_running=0 athena_daed_recovery_emitted=0
	athena_daed_recovery_stopped=0 athena_daed_recovery_restored=0 athena_daed_recovery_backup_path=""
	athena_daed_recovery_database_dirty=0 athena_daed_recovery_succeeded=0
	athena_daed_recovery_cleanup() {
		athena_daed_recovery_status=$?
		trap - 0 HUP INT TERM
		if [ "$athena_daed_recovery_succeeded" != 1 ] && [ "$athena_daed_recovery_database_dirty" = 1 ]; then
			"${ATHENA_DAED_INIT:-/etc/init.d/daed}" stop >/dev/null 2>&1 || true
			if athena_daed_recovery_wait_stopped && athena_daed_recovery_restore_backup; then
				athena_daed_recovery_database_dirty=0
			fi
		fi
		if [ "$athena_daed_recovery_was_running" = 1 ] && [ "$athena_daed_recovery_stopped" = 1 ] && [ "$athena_daed_recovery_restored" != 1 ]; then
			if "${ATHENA_DAED_INIT:-/etc/init.d/daed}" start >/dev/null 2>&1 && athena_daed_recovery_wait_ready; then
				athena_daed_recovery_restored=1
			fi
		fi
		[ "$athena_daed_recovery_locked" = 1 ] && athena_unlock
		unset athena_daed_recovery_output athena_daed_recovery_remaining athena_daed_recovery_line athena_daed_recovery_value
		unset athena_daed_recovery_username athena_daed_recovery_password athena_daed_recovery_next_username athena_daed_recovery_next_password
		return "$athena_daed_recovery_status"
	}
	athena_daed_recovery_fail_once() {
		[ "$athena_daed_recovery_emitted" = 1 ] || {
			athena_daed_recovery_json_error "$1" "${2:-}"
			athena_daed_recovery_emitted=1
		}
	}
	athena_daed_recovery_signal() {
		athena_daed_recovery_fail_once 'recovery interrupted' "$athena_daed_recovery_backup_path"
		exit "$1"
	}
	trap 'athena_daed_recovery_cleanup' 0
	trap 'athena_daed_recovery_signal 129' HUP
	trap 'athena_daed_recovery_signal 130' INT
	trap 'athena_daed_recovery_signal 143' TERM
	athena_lock daed-recovery || { athena_daed_recovery_fail_once 'recovery is already running'; exit 1; }
	athena_daed_recovery_locked=1
	if "${ATHENA_DAED_INIT:-/etc/init.d/daed}" enabled >/dev/null 2>&1; then
		athena_daed_recovery_was_enabled=1
	else
		athena_daed_recovery_was_enabled=0
	fi
	if athena_daed_recovery_active; then
		athena_daed_recovery_was_running=1
		athena_daed_recovery_stopped=1
		"${ATHENA_DAED_INIT:-/etc/init.d/daed}" stop >/dev/null 2>&1 || true
	fi
	# A backup is useful only after both the process and GraphQL endpoint are
	# cold.  Never copy a live SQLite database or any of its journal sidecars.
	if ! athena_daed_recovery_wait_stopped; then athena_daed_recovery_fail_once 'DAED did not stop'; exit 1; fi
	if ! athena_daed_recovery_backup; then athena_daed_recovery_fail_once 'DAED backup verification failed' "$athena_daed_recovery_backup_path"; exit 1; fi
	athena_daed_recovery_database_dirty=1
	athena_daed_recovery_capture="$({ "${ATHENA_DAED_BIN:-/usr/bin/daed}" resetpass --config "$(athena_root /etc/daed)"; athena_daed_recovery_rc=$?; printf '\n__ATHENA_DAED_RESETPASS_RC_%s__' "$athena_daed_recovery_rc"; } 2>/dev/null)"
	case "$athena_daed_recovery_capture" in
	*'__ATHENA_DAED_RESETPASS_RC_0__') athena_daed_recovery_output=${athena_daed_recovery_capture%__ATHENA_DAED_RESETPASS_RC_0__} ;;
	*) athena_daed_recovery_fail_once 'DAED password reset failed' "$athena_daed_recovery_backup_path"; exit 1 ;;
	esac
	case "$athena_daed_recovery_output" in *'

') athena_daed_recovery_output=${athena_daed_recovery_output%'
'}; athena_daed_recovery_output=${athena_daed_recovery_output%'
'} ;; *) athena_daed_recovery_fail_once 'DAED reset output was invalid' "$athena_daed_recovery_backup_path"; exit 1;; esac
	case "$athena_daed_recovery_output" in *'
'*) athena_daed_recovery_fail_once 'DAED reset output was invalid' "$athena_daed_recovery_backup_path"; exit 1;; esac
	if ! athena_daed_recovery_parse_output "$athena_daed_recovery_output"; then athena_daed_recovery_fail_once 'DAED reset output was invalid' "$athena_daed_recovery_backup_path"; exit 1; fi
	if ! athena_daed_recovery_validate_database; then athena_daed_recovery_fail_once 'DAED database validation failed' "$athena_daed_recovery_backup_path"; exit 1; fi
	if [ "$athena_daed_recovery_was_running" = 1 ]; then
		"${ATHENA_DAED_INIT:-/etc/init.d/daed}" start >/dev/null 2>&1 || { athena_daed_recovery_fail_once 'DAED restart failed' "$athena_daed_recovery_backup_path"; exit 1; }
		if ! athena_daed_recovery_wait_ready; then athena_daed_recovery_fail_once 'DAED did not become ready' "$athena_daed_recovery_backup_path"; exit 1; fi
	fi
	athena_daed_recovery_restored=1
	athena_daed_recovery_database_dirty=0
	athena_daed_recovery_succeeded=1
	printf '{"ok":true,"username":"%s","password":"%s","backup":"%s"}\n' "$(athena_json_escape "$athena_daed_recovery_username")" "$(athena_json_escape "$athena_daed_recovery_password")" "$(athena_json_escape "$athena_daed_recovery_backup_path")"
	athena_daed_recovery_status=$?
	unset athena_daed_recovery_output athena_daed_recovery_username athena_daed_recovery_password
	exit "$athena_daed_recovery_status"
}
