# 刷写

1. 备份 ART/EEPROM、MAC、校准分区和原固件。
2. 校验 Artifact SHA-256。
3. 在 U-Boot `/uimage.html` 上传 `athena-v19-initramfs-uImage.itb`。
4. 访问 `http://192.168.50.1/` 与 `http://192.168.50.1:8080/`，验证 WAN、三路 Wi-Fi、NSS、DAED 默认关闭和 IoT 工具。
5. 至少完成一次重负载测试，再刷写 sysupgrade。

从 v18 升级：

```sh
sysupgrade -n /tmp/athena-v19-squashfs-sysupgrade.bin
```

不要保留 v18 的网络与 Web 配置。
