# Athena v19 主页与完整 DAED UI 嵌入设计

日期：2026-08-09  
状态：用户已批准设计方案

## 目标

修复 Athena 现代化主页在真实 LuCI 中加载失败的问题，并将 DAED 自带的完整原生 UI 嵌入 LuCI/Argon 内容区。DAED UI 必须与代理核心的运行状态解耦：即使 DAED 默认关闭、启动失败或 eBPF 被内核拒绝，用户仍能打开完整 UI；后台不可用时由 UI 显示连接失败，不以自制状态页替代原生界面。

本次修改不改变既定安全默认值：DAED 仍默认关闭，只监听 `127.0.0.1:2023`，浏览器和 LAN 不直接访问 2023 端口。

## 已确认根因

### 主页

`athena/chart.js` 当前返回一个普通冻结对象。目标 LuCI 的资源加载器会把 `require athena.chart as chart` 解析为 LuCI 类模块，并要求模块工厂返回 `L.Class` 子类；普通对象触发：

```text
"athena.chart" factory yields invalid constructor
```

现有 Node 测试直接通过 `Function(source)()` 执行文件，没有模拟 LuCI 类加载约束，因此未发现真机错误。

### DAED UI

当前 `/athena-daed/` 将全部请求反向代理到 `127.0.0.1:2023`。DAED 进程既提供 Web，又加载代理核心；当服务关闭或 eBPF 加载失败导致进程退出时，Web 资源也消失。LuCI 页面只有在进程和 API 均就绪时才创建 iframe，因此显示的是自制状态页，而不是用户要求的完整 DAED UI。

直接访问 `192.168.50.1:2023` 被拒绝是 loopback 隔离的预期行为，不应通过重新开放 LAN 监听修复。

## 选择的架构

采用“原生前端静态托管 + GraphQL 单独反向代理”。不采用依赖 DAED 进程提供 Web 的整站反向代理，也不向 LAN 开放 2023。

```text
浏览器
  └─ LuCI / Argon
      └─ 服务 → DAED
          └─ iframe /athena-daed/
              ├─ HTML/CSS/JS → Nginx 静态文件
              └─ GraphQL     → /athena-daed/graphql
                                   └─ 127.0.0.1:2023/graphql
```

## 主页模块设计

`athena/chart.js` 改为标准 LuCI 类模块，返回 `L.Class.extend({...})`。公开方法保持不变：

- `appendSample`
- `deltaRate`
- `cpuPercent`
- `normalizeSeries`
- `polylineSegments`

`dashboard.js` 继续通过 `require athena.chart as chart` 使用实例方法，现代化卡片、SVG 图表、三秒轮询、两次失败告警及最大 200 个采样点均保持不变。

Node 回归测试必须使用与真实 LuCI 一致的最小类加载器替身，验证模块工厂返回可实例化的 LuCI 子类，而不再只验证普通 JavaScript 对象。

## DAED 原生 UI 构建与安装

固定来源 DAED 组装流程已经执行前端构建。本次直接复用同一份构建产物，不下载或维护第二套 UI：

1. 继续在锁定的 DAED Web 源码中将 GraphQL 端点修补为同源 `/athena-daed/graphql`。
2. Web 构建成功后，保留用于嵌入 DAED 二进制的产物。
3. 同时把未 gzip 删除的完整 `dist` 产物复制到 OpenWrt 已暂存的 `luci-app-athena` 包构建目录。
4. `luci-app-athena` 安装阶段将其放入 `/www/athena-daed/`。
5. 缺少 `index.html`、主 JavaScript、主 CSS、logo 或任何构建清单中的资源时立即失败，不生成不完整固件。

DAED Vite 配置使用相对资源基准 `./`，因此静态资源能够从 `/athena-daed/` 子路径加载。构建和离线检查仍需验证 HTML 中没有指向 `:2023` 的浏览器端地址。

## Nginx 路由

Nginx 使用两个职责分离的 location：

```text
/athena-daed/          静态 DAED 原生 UI，SPA 路由回退到 index.html
/athena-daed/graphql   反向代理到 127.0.0.1:2023/graphql
```

GraphQL location 必须优先于静态 location，保留 WebSocket 升级、长连接、禁止缓冲以及合理连接超时。静态资源不得经过 DAED 进程。

不新增 `0.0.0.0:2023` 或 `192.168.50.1:2023` 监听，不增加 WAN 防火墙规则。

## LuCI 页面行为

`服务 → Athena 优化 → DAED 面板` 始终渲染 `/athena-daed/` iframe，不再以 `daed_running && daed_api_reachable` 作为显示 UI 的前置条件。

页面保留 Argon 左侧导航和顶栏；iframe 内保留 DAED 的完整原生导航、状态、订阅、节点组、DNS、路由、设置和日志。LuCI 不重写 DAED 组件，也不注入修改其视觉样式的 CSS。

LuCI 可以在 iframe 上方显示一条紧凑、只读的后端连接提示，但不得以状态卡或自制配置界面替换、遮挡原生 UI。DAED 停止时 iframe 仍加载静态 UI；GraphQL 请求失败由原生 UI 展现。

## 默认状态与错误处理

- 刷入后 DAED 仍默认关闭。
- 完整 DAED UI 可立即打开。
- 用户启动 DAED 后，GraphQL 无需刷新页面之外的额外端口即可连接。
- eBPF、内存或配置错误不会导致 LuCI、Argon、DAED 静态 UI 或 8080 恢复入口消失。
- Nginx 静态文件缺失、路径越界或配置校验失败时，构建失败；真机上仍保留 `192.168.50.1:8080` 恢复入口。

## 构建缓存与来源一致性

静态 UI 必须来自与 DAED 二进制相同的锁定前端提交和同一次构建。源码缓存 manifest 增加静态 Web 产物摘要或等价校验，防止二进制与独立 UI 来自不同提交。

缓存命中时必须重新验证：

- 组件 pins；
- 归档 SHA-256；
- `/athena-daed/graphql` 同源端点；
- 不存在浏览器端 `:2023/graphql`；
- 静态 UI 文件清单及内容哈希。

任一不一致即重建缓存。

## 测试与验收

### 自动测试

1. LuCI 模块测试模拟 `L.Class`，旧普通对象实现必须失败，新实现必须可实例化并保留全部图表方法。
2. DAED 面板测试要求 iframe 无条件存在，且只使用 `/athena-daed/`，不得包含 `:2023`。
3. Nginx 测试要求静态 UI 与 GraphQL location 分离，GraphQL 仍只指向 loopback。
4. 组装测试要求同一次 DAED Web 构建同时生成嵌入二进制和 `luci-app-athena` 静态资源。
5. 缓存测试要求静态 UI 哈希属于 cache manifest。
6. 固件检查要求 rootfs 中存在完整 DAED 静态 UI、同源 GraphQL 路由和 loopback 监听配置。
7. 反向测试要求任何浏览器端 `:2023/graphql`、缺失主资源或重新开放 LAN 2023 都导致失败。

### 真机验收

1. U-Boot 仅内存启动新 initramfs。
2. 打开 LuCI 概况页，无 `factory yields invalid constructor` 或空白页面。
3. DAED 保持关闭，打开“服务 → Athena 优化 → DAED 面板”，完整原生 UI 仍显示。
4. 确认浏览器网络请求仅访问 `/athena-daed/` 与 `/athena-daed/graphql`，不访问 `:2023`。
5. 启动 DAED，确认原生 UI 的状态、订阅、节点、DNS、路由、设置和日志全部可用。
6. 人为停止 DAED，确认 UI 外壳仍加载，GraphQL 显示离线而 LuCI 不受影响。
7. 确认 LAN 和 WAN 均不能直接连接 2023，8080 恢复入口仍可用。

## 不在本次范围

- 不重写 DAED 原生 UI。
- 不把 DAED 默认改为启用。
- 不解决独立于 UI 的 DAED eBPF/内核兼容问题。
- 不改变 DNS、路由、NSS、ECM、Flow Offload、IoT SSID 或 Argon 主题策略。
- 不允许在 initramfs 验收前刷写 sysupgrade。
