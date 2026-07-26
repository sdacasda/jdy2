# Changelog

## v19.0.0-rc1

- LAN 改为 `192.168.50.1`，避免与常见光猫网段冲突。
- DAED 默认关闭并仅监听环回地址；通过 Nginx 同源嵌入 LuCI。
- Argon 深色主题为默认，Bootstrap 与 8080 恢复入口保留。
- 新增 `athena-setup`、`athena-health`、`athena-backup`、`athena-rollback`、`athena-runtime`、`athena-iot`。
- 新增国内 UDP DNS、国外代理 DoH、节点 bootstrap 直连模板。
- 新增 Steam、Xbox、游戏、Minecraft 与 BT 可选分流模板。
- 保留 NSS/Wi-Fi offload，停止 ECM frontend 与软件/硬件 Flow Offload。
- 新增可选的独立 2.4 GHz IoT 兼容 SSID。
- 所有外部源码锁定到完整提交；DAED 锁定为 `v2026.07.26` 对应提交。
- 缺少任一固件镜像、超出 6 MiB 内核槽或产物校验失败时构建失败。

## v18

- 增加 WOL、DAED、外置 BTF、雅典娜屏幕及双镜像构建。
