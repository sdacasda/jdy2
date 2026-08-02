# 独立 2.4 GHz IoT Wi‑Fi

部分智能家居只支持传统 2.4 GHz、WPA2 和 20 MHz。v19 提供默认关闭、与主 Wi‑Fi 分离的 IoT SSID：

```sh
athena-iot setup
athena-iot status
athena-iot diagnose
```

兼容模式默认使用：

- 2.4 GHz、20 MHz、国家代码 CN；
- 固定信道 1、6 或 11；
- WPA2-PSK/AES；
- PMF、802.11r/k/v、Wi‑Fi 6/HE 关闭；
- WMM 开启、SSID 可见、客户端隔离关闭；
- 加入现有 LAN，不额外创建 VLAN。

停用或删除：

```sh
athena-iot disable
athena-iot remove --yes
```

每次变更前会创建可校验备份。诊断输出不会显示 Wi‑Fi 密码、设备名称或客户端 MAC。
