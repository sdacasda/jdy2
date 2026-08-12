# v19 DAED login-recovery verification report

Date: 2026-08-11
Release metadata: `v19.0.0-rc2`
Verification host: Windows, using the bundled Codex Python 3.12 and Node.js 24 runtimes plus Git for Windows Bash. No network access was used.

## Scope and result

The feasible source-level verification suite passed. This covers the database
serialization patch, Web error-redaction patch, LuCI/RPC recovery exposure,
template-workflow removal, release metadata, package layout, templates, Web
isolation, source security scanning, Python syntax, and host-side shell syntax.

The checked source baseline before creating this report was clean at
`78315adacbe43ead84d598f19596789bac73c35b` (`docs: clarify DAED recovery
backup scope`). `git diff --check` and `git diff --cached --check` both exited
zero; `git status --short` was empty.

## Commands and exact results

All commands ran from the repository root.

| Command | Result |
| --- | --- |
| Bundled Python `unittest discover`, with the bundled Node.js directory prepended to `PATH` inside the Python process | PASS: 122 tests, 0 skipped. The Node-backed `safeErrorMessage` behavior test ran. |
| `D:\Git\bin\bash.exe --login scripts/test_runtime_scripts.sh` with `PYTHON=C:/Users/mayib/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/python.exe` | PASS: 11 runtime tests, 0 failed. |
| `python scripts/verify_project.py --root .` | PASS: Athena v19 project structure is valid. |
| `python scripts/verify_templates.py --templates packages/athena-runtime/files/usr/share/athena/templates --rules packages/athena-runtime/files/usr/share/athena/rules` | PASS: templates and rule lists are structurally safe. |
| `python scripts/verify_package_layout.py --root .` | PASS: package layout. |
| `python scripts/verify_web_config.py --root .` | PASS: Web configuration. |
| `python scripts/security_check.py --root .` | PASS: no public-source credential patterns found. |
| `python -m py_compile` over every `scripts/**/*.py` and `tests/**/*.py` file | PASS. |
| `D:\Git\bin\bash.exe --login -c "find scripts packages tests -type f -name '*.sh' -exec sh -n {} +"` | PASS: all discovered shell files parsed successfully. |
| `git diff --check`; `git diff --cached --check`; `git status --short` | PASS; no whitespace errors and clean baseline. |

`git grep -n -- 'v19.0.0-rc1' -- PROJECT.json CHANGELOG.md README.md packages scripts config docs`
found only historical changelog/planning/design references. The active
`PROJECT.json` version, release documentation regression tests, and project
verifier require and pass with `v19.0.0-rc2`.

## Pinned DAED patch applicability (offline)

No upstream repository was cloned or fetched. The tests use only committed,
checksum-validated fixtures:

| Command | Local fixture and result |
| --- | --- |
| `python scripts/tests/test_patch_daed_database.py` | PASS: 4 tests. Applies the database patch to the pinned `dae-wing` fixture at `dc503088945812c11235b35362d2bfa1a4c3bdf0`, verifies the second application is idempotent, and verifies an altered/unknown layout exits nonzero without changing either source file. |
| `python -m unittest tests.test_daed_web_patch -v`, with bundled Node.js discoverable | PASS: 8 tests, 0 skipped. Applies the Web patch to committed source-shaped fixtures for resolved DAED `671e65d2fdcd62fe6a3ec18ecda209c5addea898`; safe-error behavior, idempotence, tampered/already-patched rejection, extra leak/catch rejection, write rollback, and unexpected Makefile layout fail-closed behavior passed. |

The database and Web fixtures validate their SHA-256 manifest entries before
the patchers run. Their fail-closed cases verify that an unknown source is
not partially patched.

## Source delivery and extraction verification

After this report is committed, the release source is generated solely from
tracked files with:

```text
git archive --format=zip --prefix=jdy2-v19.0.0-rc2-source/ -o deliverables/jdy2-v19.0.0-rc2-source.zip HEAD
```

The generated archive and its adjacent SHA-256 file are intentionally ignored
by Git. `git archive` includes exactly the files tracked by the selected commit
and excludes `.git`, untracked caches, local build outputs, temporary test
trees, and the archive itself. Tracked implementation reports under
`.superpowers/` remain part of the auditable source delivery.
The archive is extracted to a fresh temporary directory and rechecked with the
Python/project/package/template/Web/security/version checks listed above. A
dry-run archive from the committed Task 8 report passed all 122 Python tests
with no skip plus every listed verifier and reported `v19.0.0-rc2`. The final
archive is regenerated after this report correction and rechecked once more;
its digest and extraction result are recorded in the adjacent delivery report
and SHA-256 file. This avoids a self-referential archive digest in the report
stored inside that same archive.

## Explicitly not executed

- The GitHub Actions workflow and its full OpenWrt firmware build were not
  executed locally. They require the remote immutable source checkout, feeds,
  build dependencies, Go toolchain, and lengthy compilation.
- Full immutable DAED source assembly and Go compilation were not run locally;
  the Go toolchain is unavailable on this host. The Node-backed JavaScript
  behavior check did run with the bundled Node.js runtime.
- No physical router was flashed. No real-device DAED first-login, recovery,
  backup, LuCI session, or post-flash verification was performed.

Accordingly, this report validates source and host-side behavior only. It does
not claim that any firmware image exists, is bootable, or is safe to flash.
