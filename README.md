# Athena AX6600 DAED + WOL Final Candidate v18

这版只需要跑一次 GitHub Actions，随后同一个 Artifact 同时提供：

- 完整功能的 `initramfs-uImage.itb`
- 对应的 `squashfs-sysupgrade.bin`

内置 DAED、luci-app-daede、匹配内核的外置 BTF、雅典娜点阵屏、中文 LuCI，以及网络唤醒 `luci-app-wol + etherwake`。

v17 保留了 v16 已经在真机验证成功的应急有线网络逻辑。完整功能 initramfs 即使标准 LAN 初始化异常，也会尝试让所有有线口响应 `192.168.1.1`。

DAED 和屏幕服务默认不自动启动。先确认 RAM 系统稳定，再逐项测试。

## 编译

上传整个项目后运行：

`Actions → Build Athena DAED Final Candidate → Run workflow`

参数仅选：

`compile_jobs = 2`

## 测试

先在 U-Boot `/uimage.html` 上传 `*initramfs*uImage.itb`。

启动后打开：

- `http://192.168.1.1/diag.html`
- `http://192.168.1.1/cgi-bin/luci/`

SSH 后运行：

```sh
athena-feature-check
```

显示屏测试：

```sh
uci set athena_led.config.enable='1'
uci commit athena_led
/etc/init.d/athena_led restart
```

断电正常上电可回到 ZqinKing 固件。只有完整功能 RAM 镜像持续稳定，才使用同一 Artifact 中的 `squashfs-sysupgrade.bin`，并且不保留设置。

## 网络唤醒

LuCI 中使用：

`网络 → 网络唤醒`

命令行测试：

```sh
etherwake -i br-lan AA:BB:CC:DD:EE:FF
```

把示例 MAC 地址替换为电脑有线网卡的 MAC。该功能负责在家中局域网发送魔术包；从外网访问路由器后台仍应通过安全 VPN，而不是把 LuCI 直接暴露到公网。
