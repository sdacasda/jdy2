# Athena v19 source-validation fix

## Observed failure

GitHub Actions run 18 stopped in `Validate source project` before dependency
installation, OpenWrt configuration, or firmware compilation.  Its diagnostic
Artifact therefore contained `BUILD_NOT_AVAILABLE.txt` and no firmware.

The failing runner invoked every host-side runtime fixture with `sh`.  On the
Ubuntu runner this selects `dash`, while the same fixtures had been validated
locally with Git Bash.  The fixtures deliberately exercise background process,
trap, and signal behavior and therefore require one explicit host shell.

## Changes

- Run host-side runtime fixtures with Bash on every platform.
- Keep deployed OpenWrt scripts portable by parsing every packaged `/bin/sh`
  entry point and library with `dash -n`.
- Print the exact names of failed runtime tests at the end of the runner.
- Preserve the complete source-validation transcript in the diagnostic
  Artifact at `diagnostics/source-validation/source-validation.log`.
- Add regression tests for the runner shell, dash syntax gate, and diagnostic
  log collection.

No router behavior, DAED configuration, LAN addressing, Wi-Fi settings, or
firmware package selection is changed by this fix.

