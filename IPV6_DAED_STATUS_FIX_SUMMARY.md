# IPv6 与 DAED 状态修复摘要

日期：2026-08-11

## 根因

1. 首页只读取 `network.interface.wan status`。设备的 IPv6 实际位于独立的 `wan6` 接口，因此 IPv6 状态被误报为未连接。
2. DAED 面板把完整 UI 的显示条件写成“进程运行且 API 探针成功”，与“仅在核心停止时显示后端未连接”的产品要求不一致。
3. GraphQL 探针检测到 `wget` 后，无论探测是否成功都会立即返回，无法使用已有的 `nc` 后备路径。

## 修复

- 合并检查 `wan` 与 `wan6` 的 `ipv6-address` 和 `ipv6-prefix`。
- 完整 DAED iframe 只由 `daed_running` 控制；`daed_api_reachable` 继续作为独立状态指标。
- 仅在 `wget` 得到有效 HTTP/GraphQL 响应时返回成功，否则继续尝试回环 TCP 探针。

## 安全边界

- DAED 仍只监听 `127.0.0.1:2023`。
- 浏览器仍通过 `/athena-daed/` 和 `/athena-daed/graphql` 同源访问。
- LAN 直接访问 `192.168.50.1:2023` 被拒绝是预期行为，不应开放该端口。
