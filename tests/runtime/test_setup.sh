#!/bin/sh
set -eu
fail() { echo "FAIL: $*" >&2; exit 1; }
ROOT="$(mktemp -d)"; trap 'rm -rf "$ROOT"' EXIT
LIB="$ROOT/lib"
MOCK_BIN="$ROOT/bin"
mkdir -p "$LIB" "$MOCK_BIN"
for file in common.sh backup.sh checks.sh; do
	ln -s "${PROJECT_ROOT:?}/packages/athena-runtime/files/usr/lib/athena/$file" "$LIB/$file"
done
# Setup must no longer load the rendering library. Loading this fixture is a
# test failure even if it never calls the renderer.
printf '%s\n' 'exit 99' >"$LIB/templates.sh"
cat >"$MOCK_BIN/athena-runtime" <<'EOF'
#!/bin/sh
printf '%s\n' "$*" >>"${ATHENA_RUNTIME_LOG:?}"
EOF
chmod +x "$MOCK_BIN/athena-runtime"
BIN="$PROJECT_ROOT/packages/athena-runtime/files/usr/bin/athena-setup"

prepare_root() {
	root="$1"
	mkdir -p "$root/etc/config" "$root/etc/daed" "$root/etc/init.d" "$root/sys/kernel/debug/ecm"
	printf "config athena 'main'\n" >"$root/etc/config/athena"
	printf 'SQLite format 3\000Athena test data\n' >"$root/etc/daed/wing.db"
	cat >"$root/etc/init.d/daed" <<'EOF'
#!/bin/sh
printf '%s\n' "$1" >>"${ATHENA_DAED_INIT_LOG:?}"
case "$1" in enabled) exit 0;; *) exit 99;; esac
EOF
	chmod +x "$root/etc/init.d/daed"
}

wing_hash() { sha256sum "$1/etc/daed/wing.db" | awk '{print $1}'; }

assert_wing_unchanged() {
	root="$1"; expected="$2"
	[ "$(wing_hash "$root")" = "$expected" ] || fail 'setup changed wing.db'
	cmp -s "$root/etc/daed/wing.db" "$ROOT/original-wing.db" || fail 'setup changed wing.db content'
}

run_setup() {
	root="$1"; mode="${2:-normal}"
	stop=1
	[ "$mode" != ecm_active ] || stop=0
	printf '%s\n' "$stop" >"$root/sys/kernel/debug/ecm/front_end_ipv4_stop"
	printf '%s\n' "$stop" >"$root/sys/kernel/debug/ecm/front_end_ipv6_stop"
	if [ "$mode" = daed_enabled ]; then
		ATHENA_ROOT="$root" ATHENA_LIBDIR="$LIB" PATH="$MOCK_BIN:$PATH" \
		ATHENA_RUNTIME_LOG="$root/runtime.log" ATHENA_DAED_INIT_LOG="$root/daed-init.log" \
		ATHENA_NGINX_OK=1 ATHENA_WEB_PORTS_OK=1 ATHENA_RECOVERY_WEB_OK=1 "$BIN" --resume
		return
	fi
	ATHENA_ROOT="$root" ATHENA_LIBDIR="$LIB" PATH="$MOCK_BIN:$PATH" \
	ATHENA_RUNTIME_LOG="$root/runtime.log" ATHENA_NGINX_OK=1 \
	ATHENA_WEB_PORTS_OK=1 ATHENA_RECOVERY_WEB_OK=1 ATHENA_DAED_ENABLED=0 \
	ATHENA_DAED_RUNNING=0 ATHENA_DAED_API_REACHABLE=0 "$BIN" --resume
}

expect_setup_failure() {
	root="$1"; mode="$2"
	set +e
	output="$(run_setup "$root" "$mode" 2>&1)"
	code=$?
	set -e
	[ "$code" -eq 2 ] || fail "$mode setup unexpectedly completed: $output"
	! grep -q '^STATE=complete$' "$root/var/lib/athena/setup-state" 2>/dev/null || fail "$mode setup wrote complete"
}

prepare_root "$ROOT"
cp "$ROOT/etc/daed/wing.db" "$ROOT/original-wing.db"
original_wing_hash="$(wing_hash "$ROOT")"
before="$(wc -c <"$ROOT/etc/config/athena")"
ATHENA_ROOT="$ROOT" ATHENA_LIBDIR="$LIB" "$BIN" --check >/dev/null
[ "$before" = "$(wc -c <"$ROOT/etc/config/athena")" ]
! ATHENA_ROOT="$ROOT" ATHENA_LIBDIR="$LIB" "$BIN" --bad >/dev/null 2>&1

run_setup "$ROOT"
grep -q '^STATE=complete$' "$ROOT/var/lib/athena/setup-state" || fail 'new setup did not complete'
[ ! -e "$ROOT/etc/athena/generated" ] || fail 'setup generated import files'
assert_wing_unchanged "$ROOT" "$original_wing_hash"
[ "$(find "$ROOT/root/athena-backups" -mindepth 1 -maxdepth 1 -type d | wc -l)" -eq 1 ] || fail 'new setup did not create one backup'
[ "$(wc -l <"$ROOT/runtime.log")" -eq 1 ] || fail 'runtime apply was not run once'
run_setup "$ROOT"
assert_wing_unchanged "$ROOT" "$original_wing_hash"
[ "$(find "$ROOT/root/athena-backups" -mindepth 1 -maxdepth 1 -type d | wc -l)" -eq 1 ] || fail 'complete setup created another backup'
[ "$(wc -l <"$ROOT/runtime.log")" -eq 2 ] || fail 'complete setup did not reapply runtime'

for legacy_state in backed_up awaiting_import validated; do
	legacy="$ROOT/$legacy_state"
	prepare_root "$legacy"
	legacy_wing_hash="$(wing_hash "$legacy")"
	mkdir -p "$legacy/root/athena-backups/existing" "$legacy/var/lib/athena"
	printf 'STATE=%s\nBACKUP_ID=existing\nGENERATED_SHA256=old\n' "$legacy_state" >"$legacy/var/lib/athena/setup-state"
	run_setup "$legacy"
	grep -q '^STATE=complete$' "$legacy/var/lib/athena/setup-state" || fail "$legacy_state did not migrate"
	assert_wing_unchanged "$legacy" "$legacy_wing_hash"
	[ "$(find "$legacy/root/athena-backups" -mindepth 1 -maxdepth 1 -type d | wc -l)" -eq 1 ] || fail "$legacy_state created another backup"
	[ ! -e "$legacy/etc/athena/generated" ] || fail "$legacy_state generated import files"
done

for state in new backed_up awaiting_import validated; do
	strict="$ROOT/strict-$state"
	prepare_root "$strict"
	strict_wing_hash="$(wing_hash "$strict")"
	if [ "$state" != new ]; then
		mkdir -p "$strict/root/athena-backups/existing" "$strict/var/lib/athena"
		printf 'STATE=%s\nBACKUP_ID=existing\n' "$state" >"$strict/var/lib/athena/setup-state"
	fi
	expect_setup_failure "$strict" daed_enabled
	assert_wing_unchanged "$strict" "$strict_wing_hash"
	grep -q '^enabled$' "$strict/daed-init.log" || fail "$state did not check DAED enablement"
	! grep -Eq '^(start|restart)$' "$strict/daed-init.log" || fail "$state setup started DAED"
done

strict_ecm="$ROOT/strict-ecm"
prepare_root "$strict_ecm"
expect_setup_failure "$strict_ecm" ecm_active

echo "PASS: setup"
