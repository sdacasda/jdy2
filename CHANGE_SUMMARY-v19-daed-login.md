# v19 DAED login-recovery change summary

Release metadata is `v19.0.0-rc2`.

- DAED's pinned `dae-wing` source is patched during immutable assembly to
  serialize SQLite connections, set a 10-second busy timeout, and propagate
  first-user transaction errors.
- The pinned DAED Web setup/login UI now uses the same-origin
  `/athena-daed/graphql` endpoint and renders only structured GraphQL error
  messages or a fixed safe fallback; raw request exceptions are not shown.
- Authenticated LuCI administrators can explicitly reset DAED credentials.
  Recovery takes a verified backup before stopping DAED, returns credentials
  once, and avoids logging or persistent plaintext storage of the password.
- The SSH recovery wrapper invokes the same guarded recovery implementation.
- The LuCI configuration-template menu/view/RPC workflow and setup import
  pause are removed. Internal DAED templates and rule lists remain packaged as
  inert reference material.
- Documentation explains loopback-only DAED access, recovery constraints,
  password-compromise handling, and the fact that recovery backups are not a
  user-operated database rollback mechanism.

The accompanying source archive is source-only. It is not firmware and is not
evidence that an image has been built, tested on hardware, or is flashable.
