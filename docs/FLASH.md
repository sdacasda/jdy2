# Test first

Use U-Boot `/uimage.html` with the initramfs image first. Run `athena-feature-check`. Test the screen manually. Leave DAED disabled until a valid configuration is imported.

Only after the full-feature RAM image remains stable, boot back into the installed firmware and flash the sysupgrade image from the same Artifact without keeping settings.

## Wake-on-LAN test

After the full-feature initramfs boots, open LuCI and use `Network → Wake on LAN`, or run:

```sh
etherwake -i br-lan AA:BB:CC:DD:EE:FF
```

Use the wired network adapter MAC address of the target PC.
