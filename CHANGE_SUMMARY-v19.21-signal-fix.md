# Athena v19 source-validation and recovery-signal fix

## Confirmed failure

GitHub Actions run 19 stopped in `Validate source project` before dependency
installation, OpenWrt configuration, or firmware compilation. Its diagnostic
Artifact therefore contains validation evidence only and no firmware.

The complete run-19 transcript identifies exactly two failures:

```text
test_common.sh: PYTHON: set PYTHON
test_daed_recovery.sh: PYTHON: set PYTHON
```

Both new tests invoke `${PYTHON:?set PYTHON}`, while the workflow invokes the
runtime runner without exporting `PYTHON`.  The v19.16 reference source does
not contain these Python-backed JSON assertions, which explains why that
version validated successfully.  This was an environment-contract regression,
not a DAED, Wi-Fi, kernel, or firmware-build failure.

## Changes

- Discover `python3` (or `python`) inside the runtime test runner and export the
  resolved command before any fixture is started.
- Fail immediately with a clear diagnostic if no Python interpreter exists.
- Run host-side runtime fixtures with Bash on every platform.
- Keep deployed OpenWrt scripts portable by parsing every packaged `/bin/sh`
  entry point and library with `dash -n`.
- Print the exact names of failed runtime tests at the end of the runner.
- Preserve the complete source-validation transcript in the diagnostic
  Artifact at `diagnostics/source-validation/source-validation.log`.
- Add a behavioral regression test that removes `PYTHON` from the environment
  and proves the runner discovers and exports `python3` itself.
- Keep regression tests for the runner shell, dash syntax gate, and diagnostic
  log collection.

No router behavior, DAED configuration, LAN addressing, Wi-Fi settings, or
firmware package selection is changed by this fix.

## Follow-up from run 20

Run 20 confirmed that the Python environment-contract repair worked: all 126
Python tests passed and the two former `PYTHON: set PYTHON` failures were gone.
The remaining Linux-only failure was:

```text
test_daed_recovery.sh: FAIL: signal_restore
```

`athena_daed_reset_password` created its own nested subshell.  When the public
operation was backgrounded or its CLI process received `TERM`, the signal hit
the outer process while the inner process owned the cleanup trap.  DAED could
therefore remain stopped and the recovery lock could remain until the orphaned
inner process finished.

The recovery function now installs its traps in the calling process.  A
forceable host regression test reproduces the Linux signal path locally and
checks that DAED is restarted, the lock is released, one JSON error is emitted,
and the generated password is not leaked.
