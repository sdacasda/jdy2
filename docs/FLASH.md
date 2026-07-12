# Flash and recovery

## Do not begin with sysupgrade

Use the generated initramfs image first:

`*jdcloud_re-cs-02*initramfs*uImage.itb`

Load it through the custom U-Boot Web “boot uImage” page. An initramfs RAM boot is the validation gate after the earlier boot-loop incident.

## Checks during RAM boot

SSH into the temporary system and run:

```sh
sh /verify-after-flash.sh
```

Or copy/run `verify-after-flash.sh` from the Artifact.

Also check:

```sh
ubus call system board
ip -br addr
wifi status
ls -lh /usr/lib/debug/boot/vmlinux
opkg list-installed | grep -E 'daed|daede|vmlinux-btf|athena-led|sched-bpf'
```

Open LuCI at `192.168.1.1`. DAED is intentionally disabled until configured.

## Persistent installation

Only after the RAM image remains stable:

1. Reboot to the current known-good installed LibWrt.
2. Open LuCI firmware upgrade.
3. Upload only `*jdcloud_re-cs-02*squashfs-sysupgrade.bin`.
4. Do not keep settings.
5. Do not force the flash if the compatibility check rejects the image.
6. Never upload the GitHub Artifact ZIP itself.

## Kernel partition

Both physical `HLOS` and `HLOS_1` are 6 MiB. The workflow enforces the same `6144k` source limit. Do not change it to 8 MiB merely to make a build pass.

## Recovery

Keep the custom U-Boot available. A failed initramfs test requires no eMMC restoration: power-cycle to return to the installed firmware. A failed persistent flash should be recovered with a previously known-good RE-CS-02 sysupgrade or a known-good initramfs.
