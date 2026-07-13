# Build

Pinned LiBwrt commit: `cf9444c1b20458687898489b36e1aebf56d9baf2`.
DAED release: `v2026.07.09`.
Target: `qualcommax/ipq60xx`, device `jdcloud_re-cs-02`.
One workflow run builds both RAM and persistent images.

## Wake-on-LAN

The image explicitly selects `luci-app-wol`, `etherwake` and `luci-i18n-wol-zh-cn`. The LuCI application also declares `etherwake` as its package dependency.
