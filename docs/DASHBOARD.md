# Athena 实时仪表盘

登录 LuCI 后，“状态 → 概况”和“服务 → Athena 优化 → 状态”都会打开现代化只读仪表盘。原有路由、防火墙、日志、进程和实时信息页面仍然保留。

## 卡片与图表

页面每 3 秒读取一次本机状态，并在浏览器内最多保存 200 个采样点（约 10 分钟）。刷新页面会清空历史；数据不会写入闪存或上传外部服务，也不加载 CDN 图表库。

仪表盘显示：

- 系统运行时间、负载、内核与时间同步；
- CPU、内存实时使用率与趋势；
- WAN 地址、链路状态、RX/TX 实时速率；
- 三路无线、独立 2.4 GHz IoT SSID 与客户端数量；
- DAED 的安装、启用、进程、API 与错误分类；
- NSS、Wi‑Fi offload、ECM frontend、Flow Offload；
- CPU、NSS 和无线温度趋势。

第一次采样没有可比较计数器，因此速率显示“—”。计数器回退按 0 处理，不产生负速率、`NaN` 或 `Infinity`。一次读取失败时保留最后数据，连续两次失败才提示中断。

## DAED 状态含义

DAED 默认关闭是安全发布策略，不是故障。状态卡会分别显示：

1. 服务是否设为开机启用；
2. DAED 进程是否实际运行；
3. `127.0.0.1:2023` 的 GraphQL API 是否可用。

如果 eBPF 校验失败，面板会显示兼容性错误，而不是空白 iframe。只有进程和 API 均可用时才加载 DAED 原生页面。

## 告警

- DAED eBPF 不兼容：识别 `local_tcp_sockops` 等加载错误；
- 系统时间异常：1970 年或明显未同步；
- WAN 断开或默认出口缺失；
- DNS 转发、bootstrap、SERVFAIL 异常；
- 预期无线或 IoT SSID 离线；
- 默认 80°C 温度告警、90°C 严重告警。

仪表盘不会返回 Wi‑Fi 密码、节点链接、订阅地址、UUID、Token、私钥、完整 DAED 日志或客户端 MAC。

## 恢复入口

如果主 Web 页面无法访问，请从 LAN 打开：

```text
http://192.168.50.1:8080/
```

该入口只用于诊断与恢复，不应从 WAN 暴露。详细步骤见 [WEB_RECOVERY.md](WEB_RECOVERY.md)。

## initramfs 验收

写入 sysupgrade 前，必须先用 U‑Boot 启动 initramfs 并确认：

1. `192.168.50.1` 的 LuCI 与 `192.168.50.1:8080` 恢复入口均可访问；
2. 仪表盘正常刷新，无负速率、`NaN` 或 `Infinity`；
3. Argon 深浅模式、主题色和移动端布局可用；
4. WAN、CPU、内存、温度、三路 Wi‑Fi 与 IoT 数据合理；
5. DAED 关闭时 LuCI 正常，启用后进程和 API 状态准确；
6. DAED 仍只监听 `127.0.0.1:2023`；
7. ECM frontend 与 Flow Offload 保持停止；
8. 缺失 IPv6、ECM、IoT 或部分温度传感器时，其他卡片继续刷新。

只有基础网络、三路无线、IoT SSID、DAED 面板和恢复入口全部通过后，才可考虑刷写 sysupgrade。
