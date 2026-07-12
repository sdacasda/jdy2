# Static audit record

The local project generator validated:

- shell syntax for every `.sh` file;
- Python syntax and project invariants;
- workflow YAML parsing;
- LF line endings;
- absence of merge-conflict markers;
- exact source commit pin;
- detached-BTF configuration;
- initramfs and sysupgrade collection;
- 6 MiB persistent-kernel guard;
- ZIP integrity.

This is a static project validation. A complete GitHub cloud build and an RE-CS-02 RAM boot remain required before persistent flashing.

## v14 regression guard

A synthetic copy of the current upstream DAED BTF choice was patched locally.
Validation confirms that the conditional dependency and both `DAED_USE_*`
symbols are removed and that `+vmlinux-btf` remains.

