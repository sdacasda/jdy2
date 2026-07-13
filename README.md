# Athena AX6600 RAM Diagnostic v15

这不是正式固件，而是一份只在内存中启动的极小诊断镜像。

它固定使用当前 ZqinKing 稳定固件对应的 LiBwrt 源码提交，只保留：

- RE-CS-02 设备和无线基础；
- NSS 稳定基线；
- 有线网口；
- Ping、SSH；
- 一个简单网页。

它明确不包含：

- DAED；
- BTF；
- 雅典娜屏幕插件；
- sysupgrade；
- factory；
- IMG；
- 任何持久写盘镜像。

## 目的

先确认“相同稳定内核基线 + 极小 initramfs”能否通过新版 U-Boot 正常启动并提供网络。

如果这个极小镜像能访问 `192.168.1.1`，说明此前 v14 更可能是附加功能、镜像体积或配置组合造成的问题，可以再逐项加入 DAED。

如果这个极小镜像仍完全没有网络，在不接串口的前提下就应停止自编译固件路线，不再尝试刷写 sysupgrade。

## 使用

GitHub Actions 运行 `Build Athena RAM Diagnostic`，参数 `compile_jobs=2`。

下载 Artifact 后，只能在 U-Boot `/uimage.html` 中选择：

`*jdcloud_re-cs-02*initramfs*uImage.itb`

电脑设置：

- IP：192.168.1.2
- 掩码：255.255.255.0
- 网关：192.168.1.1

等待最多 4 分钟，依次测试每个网口：

```text
ping 192.168.1.1
http://192.168.1.1
ssh root@192.168.1.1
```

断电后不按任何按键正常上电，会回到 eMMC 中的 ZqinKing 固件。
