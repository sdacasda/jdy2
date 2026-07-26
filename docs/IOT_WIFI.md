# 2.4 GHz IoT 兼容网络

很多智能家居只支持 WPA2、20 MHz 和传统 2.4 GHz。v19 提供一个默认关闭、与主 Wi-Fi 分离的兼容 SSID：

```sh
athena-iot setup
athena-iot status
athena-iot diagnose
```

默认特性：WPA2-PSK/AES、PMF 关闭、20 MHz、CN、固定信道 1/6/11、802.11r/k/v 关闭、WMM 开启、SSID 可见、客户端隔离关闭、Wi-Fi 6/HE 关闭。它加入现有 LAN，不创建新 VLAN。

停用或移除：

```sh
athena-iot disable
athena-iot remove --yes
```

每次修改前自动创建可校验备份。诊断不会显示 SSID、密码、客户端名称或 MAC。
