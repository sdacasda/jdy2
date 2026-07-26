# 架构

LuCI/Argon 由 Nginx 提供，`/athena-daed/` 反向代理至 `127.0.0.1:2023`。恢复 uhttpd 仅绑定 LAN 的 `192.168.50.1:8080`。

DAED 负责透明代理和 DNS 分流；dnsmasq 保留 DHCP/本地名称职责。SmartDNS 不内置。NSS 固件、数据面和无线 offload 保留，ECM L3/L4 前端与 Flow Offload 停止，避免绕过 DAED。
