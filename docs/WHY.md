# Why this diagnostic exists

The prior full DAED initramfs produced no reachable network and no serial
console is available. This build removes all nonessential variables.

A successful RAM boot proves:

- U-Boot FIT upload works;
- the pinned LiBwrt kernel boots;
- the RE-CS-02 device tree initializes;
- user space starts;
- at least one Ethernet interface responds.

A failed RAM boot does not write eMMC, but it also cannot be diagnosed further
without early-boot output. Persistent flashing is therefore prohibited.
