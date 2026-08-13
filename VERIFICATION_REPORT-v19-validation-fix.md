# Athena v19 source-validation verification

Date: 2026-08-13

## Artifact diagnosis

- Inspected `Athena-AX6600-v19-19-test.zip` and its preserved
  `diagnostics/source-validation/source-validation.log`.
- Confirmed the only runtime failures were `test_common.sh` and
  `test_daed_recovery.sh`, both caused by `PYTHON: set PYTHON`.
- Compared those files and the runner against the supplied working v19.16
  source ZIP. The Python-backed assertions are new after v19.16, while the
  caller still did not export `PYTHON`.
- Confirmed validation failed before dependency installation or firmware
  compilation, so run 19 contains no flashable image.
- Inspected `Athena-AX6600-v19-20-test.zip` and its preserved validation log.
  Run 20 passed all Python tests and failed only the Linux signal recovery
  assertion `signal_restore`; its Artifact is diagnostic-only and contains no
  firmware.

## Verification performed

- New unset-`PYTHON` behavioral regression: failed before the fix and passed
  after the runner began discovering/exporting Python.
- Python discovery: 126 tests passed, 1 environment-dependent Node behavior
  test skipped by discovery.
- Direct Node dashboard test: passed.
- Runtime runner: 11 tests run, 0 failed.
- Forced signal regression: reproduced `FAIL: signal_restore` before the
  recovery-process fix, then passed after the fix. The test validates restart,
  unlock, one-line JSON output, nonzero status, and secret non-disclosure.
- Pinned DAED database patch tests: 4 passed.
- Packaged shell syntax: all runtime libraries, commands, init service, and
  rpcd entry point passed `dash -n`.
- Project structure verifier: passed.
- DAED template/rule verifier: passed.
- Package layout verifier: passed.
- Web configuration verifier: passed.
- Public-source credential scan: passed.
- `git diff --check`: passed.

## Remaining external verification

The complete OpenWrt firmware build is intentionally performed by GitHub
Actions. A new Actions run is still required to prove the Ubuntu runner and
the multi-hour firmware compilation. If validation fails again, the Artifact
will preserve the complete validation transcript and the exact failed tests.

## Task 1 runtime baseline audit (2026-08-13)

Initial `git diff`/`git status --short` audit found dirty changes in the
workflow, DAED recovery implementation, runtime runner, DAED recovery test,
this report, the change summary, and `tests/test_runtime_runner.py`. The
workflow's source-validation-artifact collection is outside this task and is
deliberately left unstaged.

The baseline runner (`b7bfbd0`) was executed against a temporary fixture with
`test_daed_recovery.sh` failing and a later sentinel test. It returned 1 but
ran the sentinel, printed only a count, and omitted the failing path. This
proves the regression test fails against the pre-fix behavior.

The runner now captures each child status immediately outside `if !`, reports
`FAIL: <test> (exit <status>)`, and exits before later tests. It prints exactly
one `PASS: all runtime tests` marker only after all runtime tests, the pinned
Python test, and the packaged-shell syntax checks succeed. The regression
fixture exercises both `bash` and `sh`, and also verifies Python discovery
with an unset `PYTHON` environment.

The forced signal fixture runs recovery in its background child and leaves the
fixture EXIT trap disabled until `wait` reaps that child. This prevents a
trap-restoration race. The existing production change from a nested subshell
to the signal-owning recovery process is retained because the forced test
reproduces `signal_restore` before that change and passes with it.

Task 1 checks:

- `python -m unittest -v tests.test_runtime_runner`: 4 passed.
- `ATHENA_FORCE_SIGNAL_TEST=1 ATHENA_RUNTIME_TEST_SHELL=bash bash scripts/test_runtime_scripts.sh`: 11 runtime tests, 0 failed; one final success marker.
- `ATHENA_FORCE_SIGNAL_TEST=1 ATHENA_RUNTIME_TEST_SHELL=sh sh scripts/test_runtime_scripts.sh`: 11 runtime tests, 0 failed; one final success marker.
- `git diff --check`: passed.
