# Athena AX6600 DAED v19.0.0-rc1

面向京东云雅典娜 RE-CS-02 的稳定优先 OpenWrt 固件构建项目。一次 GitHub Actions 构建同时生成 initramfs 测试镜像和 sysupgrade 镜像；必须先完成内存启动验证，才能考虑持久刷写。

## 主要特性

- LAN 固定为 `192.168.50.1/24`，避免与常见光猫的 `192.168.1.1` 冲突。
- Nginx 独占 80/443，提供 LuCI 与 DAED 同源入口。
- uHTTPd 只监听 `192.168.50.1:8080`，作为独立恢复入口。
- DAED 默认关闭；启用后只监听 `127.0.0.1:2023`，不向 LAN/WAN 暴露管理端口。
- DAED 前端通过 `/athena-daed/` 和 `/athena-daed/graphql` 访问，不再让浏览器直连 2023。
- Argon 为默认主题，保留明暗、配色、背景和透明度设置；Bootstrap 用于恢复。
- 现代化只读首页提供 CPU、内存、WAN、温度、Wi-Fi、DAED、NSS/ECM 等卡片和本地 SVG 曲线。
- DAED 状态分为“开机启用、进程运行、API 可达”，eBPF 启动失败不会拖垮 LuCI。
- 可选独立 2.4 GHz IoT SSID，面向只支持 WPA2/20 MHz 的智能家居。
- 提供 `athena-setup`、`athena-health`、`athena-backup`、`athena-rollback`、`athena-runtime` 和 `athena-iot`。
- 保留 NSS 数据面与 Wi-Fi offload，停止 ECM frontend 和 OpenWrt Flow Offload。
- 不内置 SmartDNS、OpenClash、PassWall 或 HomeProxy。

## 默认网络策略

- 国内 IPv4/IPv6：直连。
- 国外 IPv4/IPv6：进入用户选择的 DAED 代理组。
- 国内 DNS：AliDNS/DNSPod UDP 直连。
- 国外 DNS：DoH 经代理。
- 节点与订阅域名：独立 bootstrap DNS 直连，避免解析回环。
- Steam 商店/登录可代理，下载 CDN 可直连。
- 指定游戏设备 UDP、Minecraft 和 DSCP `0x4` 的 BT 流量可选择性直连。

## Web 入口

```text
主 LuCI：   https://192.168.50.1/
恢复入口：  http://192.168.50.1:8080/
DAED 面板： LuCI → 服务 → Athena 优化 → DAED 面板
端口 2023：仅路由器回环地址可访问
```

DAED 默认关闭是安全发布策略，不是故障。导入节点和模板后再启动。

## 构建与测试

1. 将整个仓库上传到 GitHub。
2. 运行 `Build Athena AX6600 DAED v19`。
3. 建议参数：`Parallel jobs=2`、`Runtime profile=stable`、`Artifact stage=test`。
4. 下载 Artifact 并校验 `SHA256SUMS.txt`。
5. 先用 U-Boot 启动 `athena-v19-initramfs-uImage.itb`。
6. 在内存系统中运行 `tools/verify-after-flash.sh` 并完成真机清单。
7. 只有全部关键项目通过后，才可考虑 `athena-v19-squashfs-sysupgrade.bin`。

从 v18 升级必须清空旧配置：

```sh
sysupgrade -n /tmp/athena-v19-squashfs-sysupgrade.bin
```

## DAED eBPF 兼容性

仓库会删除 Feed 中冲突的 `daed 1.27.0-r1`，并强制选择锁定的 `2026.07.26-r1`。CI 在编译前后验证实际注册和编译来源，避免再次出现：

```text
local_tcp_sockops: program of this type cannot use helper bpf_get_current_task#35
```

锁定的 DAED 包不再直接依赖上游 `daed-src` Release 资产。CI 会读取锁定仓库中的 `ci/pins.env`，从不可变的 DAED、Wing、Core、Outbound 和 quic-go 提交重新组装源码，在编译前构建并嵌入已修补的 Web 页面，然后把源码包放入 OpenWrt `dl/`。`package/daed/download` 会先单独校验该文件，只有通过后才开始完整固件编译。

组装来源和实际 SHA-256 会写入 Artifact：

```text
diagnostics/daed-source-provenance/
├── pins.env
├── archive.json
├── archive.sha256
└── openwrt-download-check.log
```

云端编译成功仍不能替代真机测试。DAED 启动后必须确认进程和 API 均可达，且日志不再出现上述 FATAL。

## 首次配置

```sh
athena-setup --check
athena-setup
athena-health --verbose
```

IoT 设备无法连接主 Wi-Fi 时：

```sh
athena-iot setup
athena-iot diagnose
```

更多说明见 [构建](docs/BUILD.md)、[刷写](docs/FLASH.md)、[首次设置](docs/SETUP.md)、[Web 恢复](docs/WEB_RECOVERY.md)、[IoT Wi-Fi](docs/IOT_WIFI.md) 和 [恢复](docs/RECOVERY.md)。

> 刷机有风险。正式刷写前必须备份 ART/EEPROM、MAC、校准分区和现有固件，并完成 initramfs 真机验证。
