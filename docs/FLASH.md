# Flash and acceptance guide

Before flashing:

- confirm RE-CS-02;
- back up calibration/ART and network settings;
- prepare U-Boot or TTL recovery;
- verify SHA256;
- select the RE-CS-02 sysupgrade image;
- disable “keep settings” for the first migration.

Default address:

```text
http://192.168.50.1
```

After flashing, upload and run `verify-after-flash.sh`. Do not enable DAED unless
it prints:

```text
RESULT=READY_FOR_DAED_CONFIGURATION
```

Never run DAED together with PassWall, OpenClash, HomeProxy or another
transparent proxy.
The expected BTF mode for v9 is `detached-vmlinux-btf`. It is normal for
`/sys/kernel/btf/vmlinux` to be absent when `/usr/lib/debug/boot/vmlinux`
exists and the verifier reports readiness.

