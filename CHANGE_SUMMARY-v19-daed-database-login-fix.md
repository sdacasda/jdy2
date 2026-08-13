# DAED Database Login Repair — Change Summary

Date: 2026-08-13

This change set makes the pinned DAED database/login path safer while retiring
the obsolete Athena configuration-template workflow.

- Database serialization is applied to the immutable DAED source before
  assembly, constraining SQLite to one open and idle connection and setting a
  10-second busy timeout.
- Transaction handling propagates `BeginTx` and deferred `Commit` errors to
  callers, so a failed database write cannot look successful.
- The patched native DAED Web client exposes only GraphQL error messages and
  falls back to a fixed failure message; request variables and passwords are
  not rendered.
- Password recovery uses the exact confirmation phrase, exclusive locking,
  checksum-verified database/sidecar backups, strict one-line parsing,
  restoration of the prior DAED state, and cleanup on signals. Credentials are
  returned once by the root-owned CLI path and are not stored in status data.
- The LuCI panel keeps the original same-origin `/athena-daed/` UI when DAED
  runs but its API is unavailable, while the stopped state renders no iframe.
- The template generator, template/rule assets, rpcd/ACL wiring, verifier, CI
  invocation, setup flow, tests, and user documentation were removed rather
  than merely hidden.
- CI now binds both source patches to cache/provenance, validates static Web
  provenance, fails closed when a required build stage is not successful, and
  emits diagnostics rather than firmware-looking artifacts for incomplete
  builds.
- Local verification fixtures now supply the seven prerequisite CI outcomes,
  test both successful collection and explicit failed-outcome diagnostics,
  assert the workflow's current validation/provenance logs, and make default
  `unittest discover` recurse through the `tests` package.

Local verification evidence, including prior runtime-host timeouts and items
not runnable on this Windows host, is recorded in
`VERIFICATION_REPORT-v19-daed-database-login-fix.md`.
