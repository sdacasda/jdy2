# 刷写说明

1. 备份 ART/EEPROM、MAC、校准分区和原固件。
2. 校验 Artifact 根目录与 `firmware/SHA256SUMS`。
3. 在 U-Boot `/uimage.html` 上传 `athena-v19-initramfs-uImage.itb`。
4. 验证 `https://192.168.50.1/` 与 `http://192.168.50.1:8080/`。
5. 运行 `tools/verify-after-flash.sh`，检查 WAN、三路 Wi-Fi、NSS、DAED 安全默认、IoT 工具及 Web 端口。
6. 启动 DAED，确认进程和 API 均可达，且无 `LocalTcpSockops` FATAL。
7. 至少完成一次重负载与重启测试。
8. 全部通过后才可考虑 sysupgrade。

从 v18 升级不得保留旧配置：

```sh
sysupgrade -n /tmp/athena-v19-squashfs-sysupgrade.bin
```

之前的测试只是内存运行时，重启即可回到原系统；不要把尚未通过验证的测试镜像写入持久分区。
