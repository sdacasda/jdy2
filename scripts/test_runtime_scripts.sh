#!/bin/sh
set -u

PROJECT_ROOT="${PROJECT_ROOT:-$(CDPATH= cd -- "$(dirname "$0")/.." && pwd)}"
export PROJECT_ROOT
if ! command -v sha256sum >/dev/null 2>&1 && [ -n "${PYTHON:-}" ]; then
	ATHENA_SHA256_CMD="$PROJECT_ROOT/tests/host-bin/sha256sum"
	export ATHENA_SHA256_CMD
fi
failures=0
count=0

for test_file in "$PROJECT_ROOT"/tests/runtime/test_*.sh; do
	[ -f "$test_file" ] || continue
	count=$((count + 1))
	printf 'RUN %s\n' "${test_file##*/}"
	if ! sh "$test_file"; then
		failures=$((failures + 1))
	fi
done

printf 'Runtime tests: %s run, %s failed\n' "$count" "$failures"
[ "$failures" -eq 0 ]
