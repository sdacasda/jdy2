# Athena AX6600 DAED Clean Builder

A clean GitHub Actions project for **JDCloud Athena AX6600 / RE-CS-02** with:

- DAED full visual dashboard;
- `luci-app-daede`;
- integrated kernel BTF;
- required eBPF modules;
- Athena LED support;
- Qualcomm NSS base drivers;
- no competing transparent-proxy stack or NSS ECM.

## Create a new repository

Do not upload this project over the old `jdy` repository.

1. Create a new empty public GitHub repository.
2. Extract this ZIP locally.
3. Upload all files and hidden directories, including `.github`.
4. Run **Actions → Validate clean project**.
5. Run **Actions → Build Athena AX6600 DAED** with `build_mode=validate`.
6. After validation succeeds, rerun with `build_mode=build`.

Default inputs:

```text
source_ref: main
daede_ref: main
compile_jobs: 2
publish_release: false
```

## Flash file

From an existing OpenWrt/ImmortalWrt/LibWrt system, use only:

```text
*jdcloud_re-cs-02*sysupgrade.bin
```

For the first migration, do not preserve the old configuration.

See `docs/BUILD.md`, `docs/FLASH.md`, and `docs/UPDATE.md`.


## GitHub runner safety

This project does not use the remote ImmortalWrt environment initializer. It installs build dependencies directly and leaves the hosted runner base operating system and package sources intact.

## Flow-offload policy

The selected ImmortalWrt source installs `kmod-nft-offload` as a normal router
default package. The module being present is not treated as an error. This
project explicitly sets both `flow_offloading` and `flow_offloading_hw` to `0`
on first boot so DAED traffic is not bypassed.

## Build-order policy

The workflow never compiles `bpf-headers` as an isolated package before the
normal build. It invokes the top-level `world` target so OpenWrt prepares host
tools, the cross toolchain and the target kernel before package compilation.
## RE-CS-02 kernel-size policy

RE-CS-02 has a fixed 6144 KiB kernel slot. This project does not enlarge it.
The main kernel is built without integrated BTF; matching detached BTF is
installed in the root filesystem by `vmlinux-btf`.

Expected runtime path:

```text
/usr/lib/debug/boot/vmlinux
```

