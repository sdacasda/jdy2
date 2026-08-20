# DAED Login and Recovery Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Fix DAED SQLite login initialization, redact authentication errors, add backup-first password recovery, and remove the default configuration-template workflow.

**Architecture:** Patch the pinned dae-wing and DAED Web sources during immutable source assembly, then expose password reset through a small shared router-side recovery command and authenticated LuCI RPC. Keep internal templates as inert reference data while removing their default UI and setup integration.

**Tech Stack:** Go/GORM/SQLite, TypeScript/React, POSIX shell, OpenWrt rpcd/LuCI JavaScript, Python verification scripts, GitHub Actions.

## Global Constraints

- LAN remains `192.168.50.1`.
- DAED listens only on `127.0.0.1:2023` and is embedded through `/athena-daed/`.
- Existing `wing.db` records must be preserved.
- DAED remains disabled by default on a clean image.
- Argon remains the configurable default theme.
- SmartDNS remains excluded.
- NSS/Wi-Fi offload remain enabled while ECM frontend and flow offload remain stopped.
- No submitted or generated password may be written to logs or persistent plaintext storage.
- Internal DAED templates remain installed but are not exposed or automatically imported.

---

### Task 1: Lock the database regression requirements in tests

**Files:**
- Create: `scripts/tests/test_patch_daed_database.py`
- Modify: `scripts/test_runtime_scripts.sh`

**Interfaces:**
- Consumes: pinned dae-wing source layout `wing/db/db.go` and `wing/graphql/mutation.go`.
- Produces: executable test assertions for serialized SQLite setup and checked first-user transactions.

- [ ] **Step 1: Write a failing test** that copies the two pinned source files to a temporary tree, invokes the future patcher, and asserts `SetMaxOpenConns(1)`, `SetMaxIdleConns(1)`, `PRAGMA busy_timeout = 10000`, initial `tx.Error` handling, and commit-error propagation.
- [ ] **Step 2: Run the test** with `python scripts/tests/test_patch_daed_database.py`; expect failure because `scripts/patch_daed_database.py` does not exist.
- [ ] **Step 3: Add the test to the local verification runner** without masking its exit status.
- [ ] **Step 4: Re-run the test runner** and confirm it fails at the new test rather than an unrelated check.
- [ ] **Step 5: Commit** with `test: cover DAED database serialization`.

### Task 2: Patch the pinned dae-wing database implementation

**Files:**
- Create: `scripts/patch_daed_database.py`
- Modify: `scripts/assemble_daed_source.sh`
- Modify: `scripts/verify_daed_source_cache.py`

**Interfaces:**
- Consumes: assembled DAED source root as the first command-line argument.
- Produces: patched `wing/db/db.go`, patched `wing/graphql/mutation.go`, and cache manifest pin `DATABASE_PATCH_SHA256`.

- [ ] **Step 1: Run the Task 1 test** and retain the expected red result.
- [ ] **Step 2: Implement an idempotent Python patcher** that validates exact source anchors before inserting the connection-pool, busy-timeout, transaction-start, and commit checks; it must fail on unknown upstream layout.
- [ ] **Step 3: Invoke the patcher before `go mod tidy`** in source assembly and include its SHA-256 in `CACHE_ID` and every manifest validation/write call.
- [ ] **Step 4: Run the focused Python test and cache-verifier tests**; expect all to pass.
- [ ] **Step 5: Run `bash -n scripts/assemble_daed_source.sh`** in the available Bash environment.
- [ ] **Step 6: Commit** with `fix: serialize DAED SQLite access`.

### Task 3: Redact DAED setup and login errors

**Files:**
- Modify: `scripts/patch_daed_web.py`
- Modify: `scripts/tests/test_patch_daed_web.py`

**Interfaces:**
- Consumes: upstream `apps/web/src/pages/Setup.tsx`.
- Produces: a frontend helper that returns only GraphQL response messages or a fixed safe fallback.

- [ ] **Step 1: Extend the Web patch test** so it fails unless raw `(err as Error).message` rendering is absent from setup/signup/login catch blocks and a structured redaction helper is present.
- [ ] **Step 2: Run `python scripts/tests/test_patch_daed_web.py`** and confirm the new assertion fails.
- [ ] **Step 3: Update the idempotent Web patcher** to add the helper and operation-specific safe fallbacks without changing `/athena-daed/graphql`.
- [ ] **Step 4: Re-run the Web patch test** and confirm it passes on both a clean source fixture and an already-patched fixture.
- [ ] **Step 5: Commit** with `fix: redact DAED authentication errors`.

### Task 4: Build a shared password-recovery command

**Files:**
- Create: `packages/athena-runtime/files/usr/lib/athena/daed-recovery.sh`
- Create: `packages/athena-runtime/files/usr/bin/athena-daed-reset-password`
- Create: `scripts/tests/test_daed_recovery.sh`
- Modify: `scripts/test_runtime_scripts.sh`

**Interfaces:**
- Produces: `athena_daed_reset_password CONFIRMATION`, printing one JSON object to stdout with `username`, `password`, and `backup`, and returning nonzero on failure.
- Consumes: existing Athena lock/common helpers and `/usr/bin/daed resetpass --config /etc/daed`.

- [ ] **Step 1: Write a mock-based failing shell test** covering confirmation rejection, backup-before-stop ordering, prior-running-state restoration, and absence of the generated password from mocked logger calls.
- [ ] **Step 2: Run the focused shell test** and confirm failure because the implementation is absent.
- [ ] **Step 3: Implement the library function** with a restrictive umask, operation lock, timestamped backup, service-state capture, stop/wait/reset/restart flow, and JSON escaping.
- [ ] **Step 4: Implement the CLI wrapper** so it requests an exact confirmation phrase interactively and invokes the shared function without echoing the password to logs.
- [ ] **Step 5: Run mock tests and `sh -n`** for both files; expect pass.
- [ ] **Step 6: Commit** with `feat: add safe DAED password recovery`.

### Task 5: Expose authenticated recovery in the DAED panel

**Files:**
- Modify: `packages/athena-runtime/files/usr/libexec/rpcd/athena`
- Modify: `packages/luci-app-athena/htdocs/luci-static/resources/view/athena/daed-panel.js`
- Modify: `packages/luci-app-athena/root/usr/share/rpcd/acl.d/luci-app-athena.json`
- Modify: `scripts/tests/test_luci_app.py`

**Interfaces:**
- Produces RPC method `daed_reset_password` with required string parameter `confirmation` and response fields `ok`, `username`, `password`, `backup`, `error`.
- Consumes the Task 4 shared recovery function.

- [ ] **Step 1: Add failing LuCI/RPC static tests** for method declaration, ACL, exact confirmation input, one-time result dialog, and lack of password logging.
- [ ] **Step 2: Run the focused tests** and confirm failure.
- [ ] **Step 3: Add the RPC method** and validate that only the expected confirmation phrase reaches the recovery function.
- [ ] **Step 4: Add a destructive-action warning and reset button** to the DAED panel; render returned credentials in a nonpersistent modal that clears on close.
- [ ] **Step 5: Run LuCI/RPC tests and shell syntax checks**; expect pass.
- [ ] **Step 6: Commit** with `feat: recover DAED credentials from LuCI`.

### Task 6: Remove the configuration-template workflow

**Files:**
- Delete: `packages/luci-app-athena/htdocs/luci-static/resources/view/athena/templates.js`
- Modify: `packages/luci-app-athena/root/usr/share/luci/menu.d/luci-app-athena.json`
- Modify: `packages/athena-runtime/files/usr/libexec/rpcd/athena`
- Modify: `packages/athena-runtime/files/usr/bin/athena-setup`
- Modify: `scripts/tests/test_luci_app.py`
- Modify: `scripts/tests/test_runtime_scripts.sh`

**Interfaces:**
- `athena-setup [--check|--resume]` retains its CLI contract but no longer generates or waits for template imports.
- Internal `/usr/share/athena/templates` and `/usr/share/athena/rules` remain packaged.

- [ ] **Step 1: Write failing tests** asserting that the templates menu/view/RPC are absent and that `athena-setup` does not call `athena_render_templates` or enter `awaiting_import`.
- [ ] **Step 2: Run focused tests** and confirm failure against the current workflow.
- [ ] **Step 3: Remove the menu, view, and RPC exposure** while leaving reference files installed.
- [ ] **Step 4: Simplify `athena-setup`** to preflight, backup, runtime apply, health validation, and completion state.
- [ ] **Step 5: Run setup tests twice** to verify idempotent completion and no import pause.
- [ ] **Step 6: Commit** with `refactor: retire DAED template import workflow`.

### Task 7: Add current-device recovery documentation and release notes

**Files:**
- Create: `docs/DAED_LOGIN_RECOVERY.md`
- Modify: `README.md`
- Modify: `CHANGELOG.md`
- Modify: `PROJECT.json`

**Interfaces:**
- Documents both the v19 follow-up firmware behavior and the CLI recovery path for an already running image.

- [ ] **Step 1: Add documentation checks** for the backup-first reset command, `127.0.0.1:2023` explanation, password-compromise warning, and absence of database-deletion advice.
- [ ] **Step 2: Write the recovery guide** with verification commands and rollback location.
- [ ] **Step 3: Update project version metadata and changelog** consistently for the next RC artifact.
- [ ] **Step 4: Run project consistency and sensitive-data scans**; expect pass and confirm the exposed password is absent from the repository.
- [ ] **Step 5: Commit** with `docs: add DAED login recovery guide`.

### Task 8: Full verification and source delivery

**Files:**
- Create: `VERIFICATION_REPORT-v19-daed-login.md`
- Create: `CHANGE_SUMMARY-v19-daed-login.md`
- Produce outside repository: source ZIP and `.sha256` in the requested `jd2` directory.

**Interfaces:**
- Produces a GitHub-uploadable source tree without build caches, secrets, or `.git` internals.

- [ ] **Step 1: Run all Python, shell, project, package-layout, template, Web, and security checks** and capture exact results.
- [ ] **Step 2: Run patch applicability against the pinned local DAED source** and verify an unknown-source fixture fails closed.
- [ ] **Step 3: Review `git diff --check`, `git status`, version consistency, and forbidden-secret patterns.**
- [ ] **Step 4: Write the verification report** clearly marking the GitHub Actions firmware build and real-router login test as unexecuted if they were not run.
- [ ] **Step 5: Create a deterministic source ZIP and SHA-256** after excluding `.git`, caches, artifacts, credentials, and temporary test files.
- [ ] **Step 6: Verify the ZIP by extracting it to a temporary directory and rerunning the feasible static suite.**
- [ ] **Step 7: Commit reports** with `chore: package DAED login recovery release`.
