# DAED 后端连接状态修复摘要

日期：2026-08-10

## 问题

LuCI 同时显示“进程运行正常”和“API 未就绪”，但嵌入的 DAED 原生页面已经收到 GraphQL 业务错误（例如代理组没有节点）。旧健康探针使用无请求体的 HTTP GET，并且只匹配 `wget` 的状态行；它可能把合法的 GraphQL 响应误报为 API 不可达。与此同时，旧页面在后端未就绪时仍无条件创建 iframe，导致“未连接提示”和原生界面同时出现。

## 修复

- API 健康探针改为向回环地址发送 GraphQL POST：`query AthenaHealth { __typename }`。
- GraphQL `data` 或 `errors` 响应都证明管理后端已连接；缺少节点、规则未完成等业务错误不再被误判为 API 断开。
- LuCI 仅在 `daed_running && daed_api_reachable` 时创建完整原生 DAED iframe。
- 核心停止、启动失败或 API 不可达时，不再加载 iframe，也不再显示恢复链接、健康命令或详细分类，只显示“后端未连接”。
- `athena-health` 与 LuCI RPC 共用同一个 GraphQL 健康探针，避免两个页面给出不同结论。

## 保持不变

- DAED 默认关闭，只监听 `127.0.0.1:2023`。
- 浏览器只访问同源 `/athena-daed/` 与 `/athena-daed/graphql`，不直接暴露 2023 端口。
- 完整原生 DAED UI、Argon、LAN `192.168.50.1`、IoT SSID、NSS/Wi-Fi offload、ECM frontend 与 Flow Offload 策略均未改变。

## 真机验收

1. DAED 停止时打开“服务 → Athena 优化 → DAED 面板”，确认页面不出现原生 DAED UI，只显示“后端未连接”。
2. 启动 DAED 后点击“重新检测”，确认 API 状态为正常并显示完整原生 UI。
3. 在没有向 `proxy` 组添加节点时，原生 UI 可以显示其业务提示，但 LuCI 不应再把 API 标记为未连接。
4. 添加节点并启动代理核心后，确认状态、流量统计、DNS 和路由页面正常更新。

