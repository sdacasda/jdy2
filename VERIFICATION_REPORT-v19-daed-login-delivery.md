# Athena v19 DAED login recovery — delivery verification

- Release: `v19.0.0-rc2`
- Source commit: `42be9cd`
- Archive: `jdy2-v19.0.0-rc2-source.zip`
- SHA-256: `7b5dae815d7817aeb466e44ab75ddfbd7db108c6bbb81c34d91acc5bec2c4caa`
- Verification date: 2026-08-11

The final archive was generated from tracked files with `git archive`, then
extracted into a fresh directory. The extracted tree contained no `.git`,
`__pycache__`, `.pyc`, nested `deliverables`, or untracked build output.

Final extracted-tree results:

- Python source suite: 122 passed, 0 skipped (bundled Node.js enabled).
- Runtime shell suite: 11 passed, 0 failed.
- Pinned DAED database patch suite: 4 passed, including fail-closed cases.
- Project, package-layout, template, Web, and credential verifiers: passed.
- Extracted release metadata: `v19.0.0-rc2`.

The adjacent `.sha256` file contains the same archive digest.

Not executed: GitHub Actions/OpenWrt firmware compilation, firmware boot,
router flashing, or real-device DAED login/password recovery. This is a
source archive, not a firmware image and not proof that a firmware image is
safe to flash.
