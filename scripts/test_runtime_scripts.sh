#!/bin/sh
set -u

PROJECT_ROOT="${PROJECT_ROOT:-$(CDPATH= cd -- "$(dirname "$0")/.." && pwd)}"
export PROJECT_ROOT
if [ -z "${PYTHON:-}" ]; then
	if command -v python3 >/dev/null 2>&1; then
		PYTHON="$(command -v python3)"
	elif command -v python >/dev/null 2>&1; then
		PYTHON="$(command -v python)"
	else
		printf '%s\n' 'FAIL: Python 3 is unavailable for runtime tests' >&2
		exit 1
	fi
	export PYTHON
fi
if ! command -v sha256sum >/dev/null 2>&1 && [ -n "${PYTHON:-}" ]; then
	ATHENA_SHA256_CMD="$PROJECT_ROOT/tests/host-bin/sha256sum"
	export ATHENA_SHA256_CMD
fi
failures=0
count=0
failed_names=""
test_shell="${ATHENA_RUNTIME_TEST_SHELL:-bash}"

if ! command -v "$test_shell" >/dev/null 2>&1; then
	printf 'FAIL: runtime test shell is unavailable: %s\n' "$test_shell" >&2
	exit 1
fi

for test_file in "$PROJECT_ROOT"/tests/runtime/test_*.sh; do
	[ -f "$test_file" ] || continue
	count=$((count + 1))
	printf 'RUN %s\n' "${test_file##*/}"
	if ! "$test_shell" "$test_file"; then
		failures=$((failures + 1))
		failed_names="$failed_names ${test_file##*/}"
		printf 'FAIL TEST %s\n' "${test_file##*/}" >&2
	fi
done

python_test="$PROJECT_ROOT/scripts/tests/test_patch_daed_database.py"
count=$((count + 1))
printf 'RUN %s\n' "${python_test##*/}"
if ! "${PYTHON:-python3}" "$python_test"; then
	failures=$((failures + 1))
	failed_names="$failed_names ${python_test##*/}"
	printf 'FAIL TEST %s\n' "${python_test##*/}" >&2
fi

# The host-side fixtures intentionally use Bash for deterministic process and
# signal handling.  Production OpenWrt scripts remain /bin/sh programs and are
# checked independently with dash, which is the Ubuntu/ash-compatible parser.
if command -v dash >/dev/null 2>&1; then
	for shell_file in \
		"$PROJECT_ROOT"/packages/athena-runtime/files/usr/lib/athena/*.sh \
		"$PROJECT_ROOT"/packages/athena-runtime/files/usr/bin/athena-* \
		"$PROJECT_ROOT"/packages/athena-runtime/files/etc/init.d/athena-runtime \
		"$PROJECT_ROOT"/packages/athena-runtime/files/usr/libexec/rpcd/athena
	do
		[ -f "$shell_file" ] || continue
		printf 'SYNTAX %s\n' "${shell_file#"$PROJECT_ROOT"/}"
		if ! dash -n "$shell_file"; then
			failures=$((failures + 1))
			failed_names="$failed_names syntax:${shell_file#"$PROJECT_ROOT"/}"
		fi
	done
fi

printf 'Runtime tests: %s run, %s failed\n' "$count" "$failures"
[ "$failures" -eq 0 ] || printf 'Failed runtime tests:%s\n' "$failed_names" >&2
[ "$failures" -eq 0 ]
