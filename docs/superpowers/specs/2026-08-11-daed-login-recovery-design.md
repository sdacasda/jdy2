# DAED Login and Recovery Design

**Date:** 2026-08-11  
**Target:** Athena AX6600 DAED v19.0.0-rc1 follow-up release  
**Status:** Approved

## Problem

The embedded DAED UI is reachable and the DAED core successfully loads its
eBPF programs, but first-account setup and login can fail with:

- `cannot start a transaction within a transaction`;
- `SQLITE_BUSY` / `database is locked`;
- a partially created administrator account whose password is unknown;
- browser notifications that include the complete GraphQL request variables,
  including the submitted password.

The supplied runtime log shows many concurrent first-user queries and writes
against `/etc/daed/wing.db`. The pinned dae-wing database initialization opens
SQLite without a busy timeout and without constraining the Go SQL connection
pool. The original DAED setup page also displays the raw `graphql-request`
exception message.

The LuCI "Configuration templates" page is not required for normal DAED use.
It was added for the Athena setup assistant, but the user prefers configuring
the complete original DAED UI directly.

## Goals

1. Make DAED first-user creation and login deterministic on the router.
2. Preserve existing nodes, subscriptions, routing, DNS, and user data.
3. Provide an authenticated, explicit, backup-first password recovery path.
4. Never render submitted passwords or GraphQL variables in browser errors.
5. Remove the LuCI configuration-template workflow without removing the
   internal reference templates from the firmware.
6. Keep DAED listening only on `127.0.0.1:2023` and expose the UI only through
   the existing same-origin `/athena-daed/` integration.

## Non-goals

- Do not delete or recreate `wing.db` automatically.
- Do not preconfigure a public default DAED password.
- Do not expose port 2023 to LAN or WAN.
- Do not modify user nodes, subscriptions, groups, DNS, or routing records.
- Do not reintroduce SmartDNS, ECM frontend acceleration, or flow offload.
- Do not automatically import Athena's internal DAED templates.

## Backend database fix

The immutable DAED source assembly step will apply a versioned dae-wing patch
before compiling the binary. After `gorm.Open`, database initialization will:

- obtain the underlying `*sql.DB`;
- set `MaxOpenConns(1)` and `MaxIdleConns(1)` so SQLite writes and explicit
  transactions are serialized;
- execute `PRAGMA busy_timeout = 10000` on the single pooled connection;
- fail startup if the SQL pool or pragma cannot be initialized.

First-user creation will check the initial transaction error and propagate
`Commit()` errors through the named return value. Rollback remains best-effort
when another error is already being returned.

The source-patch digest must become part of the DAED source cache identity and
assembly manifest. A stale cached archive without the database patch must be
rejected.

## Frontend error redaction

The DAED setup page will extract only GraphQL `response.errors[].message`
values. When structured errors are unavailable it will display a fixed,
operation-specific message. It must never pass the raw `graphql-request`
exception to a toast because that exception contains request variables.

The same-origin endpoint remains `/athena-daed/graphql`.

## Password recovery

Recovery is initiated only by an authenticated LuCI administrator. The flow is:

1. Require an explicit confirmation value from the UI.
2. Acquire the existing Athena operation lock.
3. Create a timestamped backup containing `wing.db` and its SQLite sidecar
   files if present.
4. Record whether DAED was enabled and running.
5. Stop DAED and wait until its process exits.
6. Run the pinned binary's supported `daed resetpass --config /etc/daed`
   command.
7. Restart DAED only if it was previously running.
8. Return the generated credentials to the authenticated caller once.
9. Do not write the generated password to system logs, UCI, setup state, or a
   persistent plaintext file.

If reset fails, the backup path and a concise error are returned; the original
database is not automatically overwritten. A separate CLI wrapper uses the
same implementation for SSH recovery.

## LuCI changes

The Athena application retains:

- Status;
- DAED Panel;
- Backup and Rollback.

The "Configuration templates" menu entry and view are removed. The DAED panel
adds a password-recovery control with a warning that it resets every DAED
account and displays the new credentials only once.

## Athena setup changes

`athena-setup` no longer renders templates or pauses for manual import. It:

1. performs preflight checks;
2. creates a backup;
3. applies `athena-runtime` policy;
4. runs health checks;
5. records completion or reports the rollback command.

The template and rule files remain under `/usr/share/athena/` as internal
advanced references, but they are not exposed through LuCI or invoked by the
default setup flow.

## Verification

Static and feasible local tests must prove:

- the dae-wing patch applies to the pinned source;
- the compiled-source cache identity includes the database-patch digest;
- the setup frontend contains a redacting error formatter and never renders a
  raw authentication exception;
- the template LuCI route and RPC method are absent;
- `athena-setup` contains no template render/import pause;
- password recovery requires confirmation, backs up first, stops the service,
  avoids logging the password, and restores the prior running state;
- shell scripts pass syntax checks and project verification remains green.

The final report must distinguish local static verification from the GitHub
Actions firmware build and real-device login test, which cannot be claimed
without running them.

## Security note

The password visible in the submitted screenshot is compromised and must not
be reused. The recovery workflow will generate a new password, and the user
should then change it again from the DAED account settings after login.
