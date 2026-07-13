# Static audit

Validated locally: shell syntax, Python syntax, workflow YAML, source pin, target, detached-BTF wiring, v16 RAM network fallback, QCN9074 firmware conflict prevention, both image collection paths, 6 MiB kernel guard, line endings, merge markers and ZIP integrity.

Real-device full-feature initramfs testing remains mandatory before persistent flashing.

## v18 WOL safeguards

Static checks require `luci-app-wol`, `etherwake` and the Simplified Chinese WOL translation in the effective configuration and runtime diagnostic script.
