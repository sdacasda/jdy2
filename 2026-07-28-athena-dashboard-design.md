# Athena AX6600 v19 现代化仪表盘设计

日期：2026-07-28  
状态：用户已批准设计，等待书面规范复核

## 1. 目标

将登录后的 LuCI `状态 → 概况` 替换为适配 Athena AX6600 的现代化
仪表盘。仪表盘使用卡片、状态徽标和实时 SVG 曲线呈现系统、网络、无线、
DAED 与 NSS 状态，同时保持较低的固件体积和运行开销。

本设计遵守以下约束：

- 使用 LuCI 原生 JavaScript、SVG 和 CSS。
- 不引入 ECharts、外部 CDN 或新的后台守护进程。
- 每 3 秒采样一次。
- 浏览器只保留最近 10 分钟，即 200 个采样点。
- 刷新页面后历史清空。
- 不为图表写入闪存。
- 直接替换登录后的默认概况页。
- 保留原有详细状态页面和恢复入口。
- 自动适配 Argon 深色、浅色、主题色、背景与透明度。

## 2. 页面结构

### 2.1 顶部状态栏

顶部状态栏显示六个关键状态：

- 互联网连接
- DAED
- IPv4
- IPv6
- 系统时间同步
- 系统运行时间

正常状态使用主题色或绿色，警告使用橙色，故障使用红色。状态项必须包含
可读文字，不能只依赖颜色。

### 2.2 核心状态卡片

首页使用响应式卡片显示：

1. CPU 使用率和 1/5/15 分钟负载
2. 内存已用、可用和百分比
3. CPU、NSS 和三路 Wi-Fi 温度
4. WAN 当前上行、下行和链路状态
5. 三路 Wi-Fi 客户端数量以及独立 IoT SSID
6. DAED、NSS、ECM frontend 和 Flow Offload 状态

桌面端默认四列，平板两列，手机单列。卡片不使用固定像素宽度。

### 2.3 实时曲线

首页显示三组 SVG 曲线：

- WAN 上行与下行速率
- CPU 使用率与内存使用率
- CPU、NSS 与 Wi-Fi 温度

页面每 3 秒取得一次快照。浏览器维护固定长度为 200 的环形数组。添加新点
后立即删除超出上限的旧点，保证页面长时间打开时内存不会持续增长。

首次采样不计算网络速率。网口重连、设备重启或计数器回绕导致新值小于旧值
时，本次速率显示为零，不得生成负数或异常尖峰。

### 2.4 告警区域

告警区域按严重程度显示：

- 管理员密码未设置
- 系统时间未同步或仍接近 1970 年
- DAED eBPF 加载失败
- WAN 断开
- DNS 异常
- 无线射频离线
- 温度超过警戒值

识别到 `LocalTcpSockops`、`bpf_get_current_task#35` 或对应 verifier 错误时，
告警文字必须明确说明“DAED 内核组件不兼容”，并提供 DAED 日志入口。系统
时间异常应单独报告，不得被描述为 eBPF 错误的原因。

## 3. 架构

### 3.1 RPC 数据接口

扩展现有 `/usr/libexec/rpcd/athena`，增加只读 `dashboard` 方法。接口从以下
来源读取当前快照：

- `/proc/stat`
- `/proc/meminfo`
- `/proc/loadavg`
- `/sys/class/net`
- `/sys/class/thermal`
- `ubus` 网络与无线状态
- DAED 进程和最近关键错误
- ECM debugfs stop flags
- NSS 模块状态
- Flow Offload UCI 状态
- 系统时间和 NTP 状态

RPC 必须返回稳定的 JSON 字段。某项数据不可用时返回 `null`、空数组或带
状态的对象，不得使整个 RPC 调用失败。

接口是只读的，不提供启动、停止、重启、配置写入或回滚能力。所有管理操作
继续由现有 Athena 和 DAED 页面承担。

### 3.2 浏览器数据流

页面首次加载时请求一份快照并渲染静态卡片。随后使用 LuCI `poll` 每 3 秒
调用一次 `dashboard`：

```text
rpcd 快照
  → 字段标准化
  → 计算网络速率
  → 更新 200 点环形缓冲区
  → 更新卡片、SVG 曲线和告警
```

页面不得直接执行 shell 命令，不得读取未经 ACL 授权的端点。

### 3.3 LuCI 集成

新增：

```text
htdocs/luci-static/resources/view/athena/dashboard.js
htdocs/luci-static/resources/athena/dashboard.css
htdocs/luci-static/resources/athena/chart.js
root/usr/share/luci/menu.d/zz-athena-dashboard.json
```

排序靠后的菜单文件将 `admin/status/overview` 指向
`athena/dashboard`。`服务 → Athena 优化 → 状态` 也指向相同视图。

不修改 Argon 上游文件，也不删除 `luci-mod-status`。原有路由、防火墙、
日志、进程、实时信息和无线详细页面保持原路径。

## 4. 视觉规则

- 使用 LuCI/Argon CSS 变量和当前主题色。
- 深色和浅色模式均保持足够对比度。
- 曲线使用本地 SVG，不使用 canvas 外部库。
- 状态不能只依赖颜色，必须同时显示图标或文字。
- 卡片、图表和告警均支持窄屏换行。
- DAED、NSS、ECM 等缩写保留英文，解释文字使用中文。
- 页面不得内嵌公网资源。

## 5. 故障降级

- 单个数据源失败：对应卡片显示“暂不可用”，其他区域继续刷新。
- 连续两次 RPC 请求失败：顶部显示“数据已中断”和最后成功更新时间。
- 图表工具加载失败：显示当前数值和简化的文字状态，不留下空白页。
- DAED 未安装或未运行：显示关闭状态，不把它误判为整个仪表盘故障。
- 不存在 ECM、IPv6、IoT SSID 或部分 thermal zone：隐藏对应细项或显示
  “不可用”，不能抛出 JavaScript 异常。
- `192.168.50.1:8080` Bootstrap 恢复入口保持不变，不依赖新仪表盘。

回退到原生 LuCI 概况页时，只需删除
`zz-athena-dashboard.json` 并重启 Web/RPC 服务，不需要重置网络、无线或
DAED 配置。

## 6. 安全与隐私

- RPC ACL 仅授予已登录管理员读取仪表盘数据的权限。
- RPC 不返回 Wi-Fi 密码、节点链接、订阅地址、UUID、Token 或私钥。
- DAED 日志只返回匹配后的错误类别、时间和脱敏摘要，不返回完整配置。
- 页面不写 UCI、不写 `/etc`、不写日志和历史数据。
- 网络地址只显示设备本身管理所需的信息，不公开上传任何数据。

## 7. 测试

### 7.1 自动测试

新增测试必须覆盖：

- RPC JSON 固定结构。
- thermal、ECM、IPv6、DAED 和 IoT 缺失场景。
- 首次网络采样。
- 网络计数器重置和回绕。
- 200 点历史上限。
- 菜单覆盖指向 `athena/dashboard`。
- Athena 状态页复用相同视图。
- 页面无外部 CDN。
- 页面和 RPC 无配置写入。
- 响应式桌面、平板、手机断点存在。
- DAED eBPF 错误映射为明确告警。
- 时间未同步映射为独立告警。

现有 Python、运行时 Shell、包布局、Web 配置、模板和安全扫描必须继续
全部通过。

### 7.2 构建验证

GitHub Actions 必须同时通过：

- 不可变 DAED 包的编译前来源校验
- 不可变 DAED 包的编译后来源校验
- 仪表盘静态检查
- 固件包清单检查
- initramfs 和 sysupgrade 产物检查

### 7.3 真机验收

先用 initramfs 验证：

- 登录后默认进入新仪表盘。
- 桌面和手机页面没有横向溢出。
- WAN、CPU、内存和温度曲线正常更新。
- 刷新后历史清空。
- 页面打开 30 分钟后仍只有 200 个采样点。
- 三路 Wi-Fi 和 IoT SSID 数量正确。
- DAED 正常、关闭和 eBPF 失败三种状态显示正确。
- 时间未同步和同步后的状态转换正确。
- Argon 深色、浅色和自定义主题色正常。
- 恢复入口仍可访问。

## 8. 非目标

本版本不实现：

- 24 小时或跨重启历史保存
- 图表数据写入闪存
- 外部遥测或云端上传
- ECharts、Chart.js 等第三方图表库
- 从仪表盘直接修改系统或 DAED 配置
- 修改 Argon 上游主题源码
