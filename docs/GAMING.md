# 游戏、Steam、Xbox 与 BT

模板将 Steam/Xbox 商店和登录域名代理，下载 CDN 直连。指定游戏设备的 UDP 可直连；Minecraft Java 25565、Bedrock UDP 19132-19133 直连。

qBittorrent 可把传出数据包服务类型设为 `4`，由 `dscp(0x4) -> direct` 识别。不要使用全局“所有 UDP 直连”，否则可能泄漏国外 QUIC/IPv6 流量。
