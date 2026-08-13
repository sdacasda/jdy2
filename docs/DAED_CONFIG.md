# DAED configuration, DNS, and routing

Athena does not generate or import DAED configuration files. Manage
subscriptions, nodes, DNS, routing, and other DAED settings directly in the
bundled native DAED UI.

Open the native UI through LuCI at **Services → Athena → DAED Panel**. The
browser must use the same-origin `/athena-daed/` path; do not connect directly
to port `2023`. GraphQL is available only through the same-origin
`/athena-daed/graphql` proxy.

Athena does not write, delete, or ask users to manually edit the DAED
`wing.db` database. Existing data is preserved.
