# Update and rollback policy

Back up `/etc/daed/wing.db`, `/etc/config/daed` and `/etc/config/daede` before
updating DAED.

Use the LuCI daede update page for DAED/dashboard/geodata updates that do not
require a new kernel.

Rebuild and reflash for kernel, BTF, NSS, wireless-driver, kmod or base-system
changes.

Every build records exact source commits. Enter those commit hashes as
`source_ref` and `daede_ref` to reproduce or roll back a build.

Never bulk-upgrade `kmod-*` packages from another build.
