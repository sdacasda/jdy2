#!/bin/sh
set -eu

fail() { echo "FAIL: $*" >&2; exit 1; }
ROOT="$(mktemp -d)"; MOCK_BIN="$(mktemp -d)"
trap 'rm -rf "$ROOT" "$MOCK_BIN"' EXIT
export ATHENA_ROOT="$ROOT" ATHENA_LIBDIR="${PROJECT_ROOT}/packages/athena-runtime/files/usr/lib/athena"
export PATH="$MOCK_BIN:$PATH" ATHENA_DAED_INIT="$MOCK_BIN/daed-init" ATHENA_DAED_BIN="$MOCK_BIN/daed"
export ATHENA_REAL_SHA256SUM="$(command -v sha256sum)"
export ATHENA_REAL_CP="$(command -v cp)"
export ATHENA_RECOVERY_TEST_LOG="$ROOT/mock.log"
export RUNNING_FILE="$ROOT/running" ENABLED_FILE="$ROOT/enabled" API_FILE="$ROOT/api"
mkdir -p "$ROOT/etc/daed" "$ROOT/var/lock"
printf 'database\n' >"$ROOT/etc/daed/wing.db"
printf 'wal\n' >"$ROOT/etc/daed/wing.db-wal"
printf 'shm\n' >"$ROOT/etc/daed/wing.db-shm"
printf 'journal\n' >"$ROOT/etc/daed/wing.db-journal"

cat >"$MOCK_BIN/pidof" <<'EOF'
#!/bin/sh
[ "${1:-}" = daed ] && [ "$(cat "$RUNNING_FILE")" = 1 ] && printf '1234\n'
EOF
cat >"$MOCK_BIN/wget" <<'EOF'
#!/bin/sh
[ "$(cat "$API_FILE")" = 1 ] && printf 'HTTP/1.0 200 OK\n'
EOF
cat >"$MOCK_BIN/sha256sum" <<'EOF'
#!/bin/sh
if [ "${DAED_SHA_FAIL:-}" = "${1:-}" ]; then exit 1; fi
exec "$ATHENA_REAL_SHA256SUM" "$@"
EOF
cat >"$MOCK_BIN/cp" <<'EOF'
#!/bin/sh
printf 'copy\n' >>"$ATHENA_RECOVERY_TEST_LOG"
exec "$ATHENA_REAL_CP" "$@"
EOF
cat >"$MOCK_BIN/sqlite3" <<'EOF'
#!/bin/sh
printf 'sqlite-check\n' >>"$ATHENA_RECOVERY_TEST_LOG"
[ "${DAED_SQLITE_FAIL:-0}" = 0 ] || exit 1
printf 'ok\n1\n'
EOF
cat >"$MOCK_BIN/daed-init" <<'EOF'
#!/bin/sh
printf '%s\n' "$1" >>"$ATHENA_RECOVERY_TEST_LOG"
case "$1" in
enabled) [ "$(cat "$ENABLED_FILE")" = 1 ] ;;
running) [ "${DAED_INIT_RUNNING:-0}" = 1 ] ;;
stop)
	[ "${DAED_STOP_STUCK:-0}" = 1 ] || printf '0\n' >"$RUNNING_FILE"
	[ "${DAED_API_STUCK:-0}" = 1 ] || printf '0\n' >"$API_FILE"
	[ "${DAED_STOP_RESULT:-0}" = 0 ] || exit "$DAED_STOP_RESULT"
	;;
start)
	printf '1\n' >"$RUNNING_FILE"
	if [ "${DAED_START_API_FAIL_ONCE:-0}" = 1 ] && [ ! -e "$ATHENA_ROOT/api-start-failed" ]; then
		printf '0\n' >"$API_FILE"; : >"$ATHENA_ROOT/api-start-failed"
	else
		printf '1\n' >"$API_FILE"
	fi
	if [ "${DAED_START_FAIL_ONCE:-0}" = 1 ] && [ ! -e "$ATHENA_ROOT/start-failed" ]; then
		: >"$ATHENA_ROOT/start-failed"; exit 1
	fi
	;;
esac
EOF
cat >"$MOCK_BIN/daed" <<'EOF'
#!/bin/sh
printf '%s\n' "$*" >>"$ATHENA_RECOVERY_TEST_LOG"
[ "${DAED_RESET_SLEEP:-0}" = 0 ] || sleep "$DAED_RESET_SLEEP"
[ "${DAED_MUTATE_DB:-0}" = 0 ] || {
	printf 'mutated-database\n' >"$ATHENA_ROOT/etc/daed/wing.db"
	printf 'mutated-wal\n' >"$ATHENA_ROOT/etc/daed/wing.db-wal"
	rm -f "$ATHENA_ROOT/etc/daed/wing.db-shm"
}
[ "${DAED_RESULT:-ok}" = ok ] || exit 1
[ "${DAED_NO_OUTPUT:-0}" = 0 ] || exit 0
if [ -n "${DAED_RAW_OUTPUT+x}" ]; then
	printf '%s\n' "$DAED_RAW_OUTPUT"
	exit 0
fi
printf 'Username: %s, Password: %s\n' "${DAED_USERNAME:-admin}" "$DAED_PASSWORD"
[ "${DAED_EXTRA_BLANK:-0}" = 0 ] || printf '\n'
[ -z "${DAED_SECOND_USERNAME:-}" ] || printf 'Username: %s, Password: %s\n' "$DAED_SECOND_USERNAME" "$DAED_PASSWORD"
EOF
chmod 0755 "$MOCK_BIN"/*
. "$ATHENA_LIBDIR/common.sh"
. "$ATHENA_LIBDIR/daed-recovery.sh"

SENTINEL='A1b2C3d4'; export DAED_PASSWORD="$SENTINEL"
reset_fixture() {
	: >"$ATHENA_RECOVERY_TEST_LOG"; printf '1\n' >"$RUNNING_FILE"; printf '1\n' >"$ENABLED_FILE"; printf '1\n' >"$API_FILE"
	export DAED_PASSWORD="$SENTINEL"
	unset DAED_INIT_RUNNING DAED_STOP_STUCK DAED_API_STUCK DAED_STOP_RESULT DAED_RESULT DAED_USERNAME DAED_SECOND_USERNAME DAED_RESET_SLEEP DAED_EXTRA_BLANK DAED_SHA_FAIL DAED_NO_OUTPUT DAED_RAW_OUTPUT DAED_MUTATE_DB DAED_SQLITE_FAIL DAED_START_FAIL_ONCE DAED_START_API_FAIL_ONCE
	rm -rf "$ROOT/root/athena-backups" "$ROOT/var/lock/athena-daed-recovery.lock"
	printf 'database\n' >"$ROOT/etc/daed/wing.db"
	printf 'wal\n' >"$ROOT/etc/daed/wing.db-wal"
	printf 'shm\n' >"$ROOT/etc/daed/wing.db-shm"
	printf 'journal\n' >"$ROOT/etc/daed/wing.db-journal"
	rm -f "$ROOT/start-failed" "$ROOT/api-start-failed"
}
run_recovery() {
	set +e
	RECOVERY_OUTPUT="$(athena_daed_reset_password "$1" 2>"$ROOT/recovery.err")"
	RECOVERY_STATUS=$?
	set -e
}
assert_one_json() {
	[ "$(printf '%s\n' "$RECOVERY_OUTPUT" | wc -l | tr -d ' ')" = 1 ] || fail json_line_count
	printf '%s' "$RECOVERY_OUTPUT" | "${PYTHON:?set PYTHON}" -c 'import json,sys; json.load(sys.stdin)' || fail invalid_json
}
assert_failure() { [ "$RECOVERY_STATUS" -ne 0 ] || fail "$1"; assert_one_json; }
assert_database_restored() {
	[ "$(cat "$ROOT/etc/daed/wing.db")" = database ] || fail "$1_database"
	[ "$(cat "$ROOT/etc/daed/wing.db-wal")" = wal ] || fail "$1_wal"
	[ "$(cat "$ROOT/etc/daed/wing.db-shm")" = shm ] || fail "$1_shm"
	[ "$(cat "$ROOT/etc/daed/wing.db-journal")" = journal ] || fail "$1_journal"
	[ "$(cat "$RUNNING_FILE")" = 1 ] && [ "$(cat "$API_FILE")" = 1 ] || fail "$1_service"
}

reset_fixture; run_recovery WRONG; assert_failure confirmation_status
[ ! -s "$ATHENA_RECOVERY_TEST_LOG" ] || fail confirmation_side_effect

reset_fixture; mkdir "$ROOT/var/lock/athena-daed-recovery.lock"; run_recovery 'RESET DAED PASSWORD'; assert_failure lock_status
[ ! -s "$ATHENA_RECOVERY_TEST_LOG" ] || fail lock_side_effect; rmdir "$ROOT/var/lock/athena-daed-recovery.lock"

reset_fixture; printf '0\n' >"$RUNNING_FILE"; printf '1\n' >"$API_FILE"
run_recovery 'RESET DAED PASSWORD'; [ "$RECOVERY_STATUS" -eq 0 ] || fail api_only_status; assert_one_json
grep -q '^stop$' "$ATHENA_RECOVERY_TEST_LOG" || fail api_only_stop; grep -q '^start$' "$ATHENA_RECOVERY_TEST_LOG" || fail api_only_restart

reset_fixture; run_recovery 'RESET DAED PASSWORD'; [ "$RECOVERY_STATUS" -eq 0 ] || fail cold_backup_status; assert_one_json
stop_line="$(grep -n '^stop$' "$ATHENA_RECOVERY_TEST_LOG" | head -n1 | cut -d: -f1)"
copy_line="$(grep -n '^copy$' "$ATHENA_RECOVERY_TEST_LOG" | head -n1 | cut -d: -f1)"
[ -n "$stop_line" ] && [ -n "$copy_line" ] && [ "$stop_line" -lt "$copy_line" ] || fail backup_must_be_cold

reset_fixture; export DAED_STOP_RESULT=1
run_recovery 'RESET DAED PASSWORD'; [ "$RECOVERY_STATUS" -eq 0 ] || fail partial_stop_status; assert_one_json
grep -q '^resetpass --config ' "$ATHENA_RECOVERY_TEST_LOG" || fail partial_stop_reset

reset_fixture; export DAED_STOP_STUCK=1; run_recovery 'RESET DAED PASSWORD'; assert_failure timeout_status
! grep -q resetpass "$ATHENA_RECOVERY_TEST_LOG" || fail timeout_reset; [ "$(cat "$RUNNING_FILE")" = 1 ] || fail timeout_restore
[ ! -e "$ROOT/var/lock/athena-daed-recovery.lock" ] || fail timeout_unlock

reset_fixture; export DAED_API_STUCK=1
run_recovery 'RESET DAED PASSWORD'; assert_failure api_stuck_status
! grep -q resetpass "$ATHENA_RECOVERY_TEST_LOG" || fail api_stuck_reset; [ "$(cat "$RUNNING_FILE")" = 1 ] || fail api_stuck_restore
[ ! -e "$ROOT/var/lock/athena-daed-recovery.lock" ] || fail api_stuck_unlock

reset_fixture; printf '0\n' >"$RUNNING_FILE"; printf '0\n' >"$API_FILE"
run_recovery 'RESET DAED PASSWORD'; [ "$RECOVERY_STATUS" -eq 0 ] || fail enabled_stopped_status; assert_one_json
! grep -q '^stop$\|^start$' "$ATHENA_RECOVERY_TEST_LOG" || fail enabled_stopped_changed
[ "$(cat "$ENABLED_FILE")" = 1 ] || fail enabled_state_changed

reset_fixture; export DAED_SHA_FAIL=manifest.txt; run_recovery 'RESET DAED PASSWORD'; assert_failure checksum_failure_status
printf '%s' "$RECOVERY_OUTPUT" | grep -q '"backup":"/' || fail checksum_failure_backup
[ "$(grep -c '^stop$' "$ATHENA_RECOVERY_TEST_LOG" || true)" = 1 ] || fail checksum_failure_stop
! grep -q '^resetpass' "$ATHENA_RECOVERY_TEST_LOG" || fail checksum_failure_resetpass
[ "$(grep -c '^start$' "$ATHENA_RECOVERY_TEST_LOG" || true)" = 1 ] || fail checksum_failure_restore
[ ! -e "$ROOT/var/lock/athena-daed-recovery.lock" ] || fail checksum_failure_unlock

reset_fixture; export DAED_RESULT=fail DAED_MUTATE_DB=1; run_recovery 'RESET DAED PASSWORD'; assert_failure reset_failure_status
assert_database_restored reset_failure_restore

reset_fixture; export DAED_NO_OUTPUT=1; run_recovery 'RESET DAED PASSWORD'; assert_failure missing_output_status
! grep -F "$SENTINEL" "$RECOVERY_OUTPUT" "$ROOT/recovery.err" "$ATHENA_RECOVERY_TEST_LOG" >/dev/null 2>&1 || fail missing_output_secret

reset_fixture; export DAED_RAW_OUTPUT='Username: admin, Password: too-short' DAED_MUTATE_DB=1; run_recovery 'RESET DAED PASSWORD'; assert_failure malformed_output_status
! grep -F 'too-short' "$RECOVERY_OUTPUT" "$ROOT/recovery.err" "$ATHENA_RECOVERY_TEST_LOG" >/dev/null 2>&1 || fail malformed_output_leak
assert_database_restored malformed_output_restore

reset_fixture; export DAED_MUTATE_DB=1 DAED_SQLITE_FAIL=1; run_recovery 'RESET DAED PASSWORD'; assert_failure sqlite_validation_status
assert_database_restored sqlite_validation_restore

reset_fixture; export DAED_MUTATE_DB=1 DAED_START_FAIL_ONCE=1; run_recovery 'RESET DAED PASSWORD'; assert_failure restart_status
assert_database_restored restart_restore

reset_fixture; export DAED_MUTATE_DB=1 DAED_START_API_FAIL_ONCE=1; run_recovery 'RESET DAED PASSWORD'; assert_failure restart_api_status
assert_database_restored restart_api_restore

reset_fixture; export DAED_SECOND_USERNAME=second; run_recovery 'RESET DAED PASSWORD'; assert_failure multiple_status
! grep -F 'Username:' "$ROOT/recovery.err" "$ATHENA_RECOVERY_TEST_LOG" >/dev/null 2>&1 || fail raw_output_logged

reset_fixture; export DAED_EXTRA_BLANK=1; run_recovery 'RESET DAED PASSWORD'; assert_failure trailing_blank_status
! grep -q resetpass "$ROOT/recovery.err" || fail trailing_blank_raw_leak

reset_fixture; export DAED_USERNAME='Jane 雪 Doe' DAED_PASSWORD='A"b\C?dE'
run_recovery 'RESET DAED PASSWORD'; [ "$RECOVERY_STATUS" -eq 0 ] || fail unicode_status; assert_one_json
printf '%s' "$RECOVERY_OUTPUT" | "${PYTHON:?set PYTHON}" -c 'import json,sys; json.load(sys.stdin)' || fail escaped_json

reset_fixture; export DAED_MUTATE_DB=1; run_recovery 'RESET DAED PASSWORD'; [ "$RECOVERY_STATUS" -eq 0 ] || fail success_status; assert_one_json
[ "$(cat "$ROOT/etc/daed/wing.db")" = mutated-database ] || fail success_new_database
[ "$(printf '%s' "$RECOVERY_OUTPUT" | grep -o "$SENTINEL" | wc -l | tr -d ' ')" = 1 ] || fail password_once
! grep -R -F "$SENTINEL" "$ROOT" "$MOCK_BIN" >/dev/null 2>&1 || fail secret_persisted
[ -z "${athena_daed_recovery_output+x}${athena_daed_recovery_password+x}${athena_daed_recovery_username+x}" ] || fail secret_global
[ ! -e "$ROOT/var/lock/athena-daed-recovery.lock" ] || fail unlock_success
success_backup="$(printf '%s' "$RECOVERY_OUTPUT" | "${PYTHON:?set PYTHON}" -c 'import json,sys; print(json.load(sys.stdin)["backup"])')"
for success_file in wing.db wing.db-wal wing.db-shm wing.db-journal manifest.txt checksums.sha256; do [ -f "$success_backup/$success_file" ] || fail "success_$success_file"; done
(cd "$success_backup" && sha256sum -c checksums.sha256 >/dev/null) || fail success_checksums
case "$(uname -s 2>/dev/null || true)" in MINGW*|MSYS*) : ;; *) [ "$(stat -c %a "$success_backup")" = 700 ] || fail success_dir_mode; [ "$(stat -c %a "$success_backup/wing.db")" = 600 ] || fail success_file_mode;; esac

reset_fixture; rm -f "$ROOT/etc/daed/wing.db"; run_recovery 'RESET DAED PASSWORD'; assert_failure missing_db_status
[ "$(grep -c '^stop$' "$ATHENA_RECOVERY_TEST_LOG" || true)" = 1 ] || fail missing_db_stop
! grep -q '^resetpass' "$ATHENA_RECOVERY_TEST_LOG" || fail missing_db_resetpass
[ "$(grep -c '^start$' "$ATHENA_RECOVERY_TEST_LOG" || true)" = 1 ] || fail missing_db_restore
printf 'database\n' >"$ROOT/etc/daed/wing.db"

case "$(uname -s 2>/dev/null || true):${ATHENA_FORCE_SIGNAL_TEST:-0}" in
MINGW*:0|MSYS*:0) : ;; # Opt in locally; Linux CI always exercises this path.
*)
	reset_fixture; export DAED_RESET_SLEEP=20
	run_signal_recovery() {
		athena_daed_reset_password 'RESET DAED PASSWORD' >"$ROOT/signal.out" 2>"$ROOT/signal.err"
	}
	# The recovery routine owns signal traps.  Keep its mutation in the child
	# process created by this background invocation, and do not restore this
	# fixture's EXIT trap until wait(1) has reaped that child.
	trap - EXIT
	run_signal_recovery & signal_pid=$!
	sleep 1; kill -TERM "$signal_pid"; set +e; wait "$signal_pid"; signal_status=$?; set -e
	trap 'rm -rf "$ROOT" "$MOCK_BIN"' EXIT
	[ "$signal_status" -ne 0 ] || fail signal_status; [ "$(cat "$RUNNING_FILE")" = 1 ] || fail signal_restore
	[ ! -e "$ROOT/var/lock/athena-daed-recovery.lock" ] || fail signal_unlock
	[ "$(wc -l <"$ROOT/signal.out" | tr -d ' ')" = 1 ] || fail signal_json_lines
"${PYTHON:?set PYTHON}" -c 'import json,sys; x=json.load(open(sys.argv[1])); assert x["ok"] is False and "interrupted" in x["error"] and x.get("backup")' "$ROOT/signal.out" || fail signal_json
! grep -F "$SENTINEL" "$ROOT/signal.out" "$ROOT/signal.err" >/dev/null 2>&1 || fail signal_secret
	;;
esac

CLI="${PROJECT_ROOT}/packages/athena-runtime/files/usr/bin/athena-daed-reset-password"
set +e; "$CLI" one two >/dev/null 2>"$ROOT/cli.err"; cli_status=$?; set -e
[ "$cli_status" -eq 64 ] || fail cli_arity
set +e; "$CLI" 'RESET DAED PASSWORD' >/dev/null 2>"$ROOT/cli.err"; cli_status=$?; set -e
[ "$cli_status" -eq 64 ] || fail cli_confirmation_argument
reset_fixture; set +e; cli_output="$(printf 'RESET DAED PASSWORD\n' | "$CLI" 2>"$ROOT/cli.err")"; cli_status=$?; set -e
[ "$cli_status" -eq 69 ] || fail cli_pipe_status
[ -z "$cli_output" ] || fail cli_pipe_capture
grep -q 'interactive terminal' "$ROOT/cli.err" || fail cli_pipe_error
[ ! -s "$ATHENA_RECOVERY_TEST_LOG" ] || fail cli_pipe_side_effect
reset_fixture; set +e; "$CLI" </dev/null >"$ROOT/cli.out" 2>"$ROOT/cli.err"; cli_status=$?; set -e
[ "$cli_status" -eq 69 ] || fail cli_redirect_status
[ ! -s "$ROOT/cli.out" ] || fail cli_redirect_capture
[ ! -s "$ATHENA_RECOVERY_TEST_LOG" ] || fail cli_redirect_side_effect

echo 'PASS: daed-recovery'
