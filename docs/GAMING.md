# 游戏、Steam、Xbox 与 BT

默认模板采用选择性直连：

- Steam/Xbox 商店、登录和账号服务：代理。
- Steam/Xbox 下载与更新 CDN：直连。
- 指定游戏设备的实时 UDP：直连。
- Minecraft Java `25565`、Bedrock UDP `19132-19133`：直连。
- qBittorrent 可将“传出数据包服务类型”设为 `4`，由 `dscp(0x4) -> direct` 识别。

不使用全局“所有 UDP 直连”，否则国外 QUIC、IPv6 UDP 和其他应用流量可能绕过代理。设备 MAC、节点地址和订阅信息只在本机填写，不应提交到公开仓库。
