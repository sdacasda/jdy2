# 系统架构

Athena v19 采用“一个主入口、一个恢复入口”的 Web 架构：

```text
浏览器
  ├─ http://192.168.50.1/       → Nginx → LuCI / Argon
  │                                  └─ /athena-daed/ → 127.0.0.1:2023
  └─ http://192.168.50.1:8080/  → uHTTPd 恢复入口（仅 LAN）
```

- Nginx 独占日常管理端口 80/443，避免与 uHTTPd 抢占端口。
- DAED 只监听 `127.0.0.1:2023`，浏览器通过同源路径 `/athena-daed/` 访问。
- uHTTPd 只绑定 `192.168.50.1:8080`，在 Nginx、Argon 或 DAED 异常时提供恢复页面。
- DAED 默认关闭；“已启用”“进程运行”“GraphQL API 可用”会分别检测和显示。

网络数据面中，dnsmasq 负责 DHCP 和本地域名，DAED 负责 DNS 分流与透明代理。固件不内置 SmartDNS。NSS 固件、数据面和 Wi‑Fi offload 保留；ECM IPv4/IPv6 frontend 与 OpenWrt Flow Offload 默认停止，避免绕过 DAED。
