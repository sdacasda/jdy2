# Athena AX6600 DAED v19.0.0-rc1

京东云雅典娜 RE-CS-02 的稳定优先固件构建项目。一次 GitHub Actions 构建同时产生 initramfs 测试镜像和 sysupgrade 镜像。

## 安全默认值

- LAN：`192.168.50.1/24`
- DAED 默认关闭，只监听 `127.0.0.1:2023`
- LuCI 使用 Argon 深色主题，Bootstrap 保留为恢复主题
- DAED 通过 LuCI 的 `服务 → Athena 优化 → DAED 面板` 同源访问
- 恢复入口：`http://192.168.50.1:8080/`
- SmartDNS、OpenClash、PassWall、HomeProxy 不内置
- 保留 NSS 数据面和 Wi-Fi offload，停止 ECM frontend 与 Flow Offload
- 独立 2.4 GHz IoT SSID 默认关闭

## 网络策略

国内 IPv4/IPv6 直连；国外流量进入用户选择的 DAED 代理组。国内域名使用直连 UDP DNS，国外域名使用经代理的 DoH，节点及订阅域名使用直连 bootstrap DNS，避免解析回环。

Steam 商店/登录可代理，下载 CDN 可直连；指定游戏设备 UDP、Minecraft 和带 DSCP `0x4` 的 BT 流量可选择直连。

## 构建与刷写

1. 上传整个仓库到 GitHub。
2. 运行 `Build Athena AX6600 DAED v19` 工作流。
3. 下载 Artifact 并校验 SHA-256。
4. **先用 U-Boot 启动 `athena-v19-initramfs-uImage.itb`。**
5. 真机验证通过后，才可刷写 `athena-v19-squashfs-sysupgrade.bin`。

从 v18 迁移必须不保留旧配置：

```sh
sysupgrade -n /tmp/athena-v19-squashfs-sysupgrade.bin
```

## 首次设置

导入自己的节点后运行：

```sh
athena-setup
athena-health --verbose
```

IoT 设备连不上主 Wi-Fi 时，创建兼容网络：

```sh
athena-iot setup
athena-iot diagnose
```

详细说明见 [docs/FLASH.md](docs/FLASH.md)、[docs/SETUP.md](docs/SETUP.md)、[docs/IOT_WIFI.md](docs/IOT_WIFI.md) 和 [docs/RECOVERY.md](docs/RECOVERY.md)。

> 刷机有风险。正式刷写前必须备份校准分区和现有固件，并完成 initramfs 真机测试。
