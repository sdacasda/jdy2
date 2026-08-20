# Athena v19 initramfs Web 与 DAED 同源入口修复设计

日期：2026-08-02  
状态：待用户最终复核  
目标版本：Athena AX6600 DAED v19.0.0-rc1 后续测试构建  
适用设备：JDCloud RE-CS-02 / Athena AX6600

## 1. 背景与结论

用户在 U-Boot 中以 initramfs 方式启动当前 v19 测试固件，未刷入持久化分区。启动后出现：

- DAED 显示已启用，但 DAED 前端无法打开；
- 默认 LuCI 管理页面也无法打开；
- 问题发生在干净的内存系统中，不存在旧 overlay、保留配置或 sysupgrade 迁移残留。

只读检查当前源码、v19 构建产物和用户提供的 BleachWrt 参考固件后，确认问题来自固件内置 Web 架构，而不是用户配置。

当前 v19 存在三个相互独立但会叠加的缺陷：

1. Nginx 和 uHTTPd 同时尝试监听 80 端口，服务启动结果依赖启动顺序；
2. DAED 的 Nginx 代理片段以 `athena-daed.conf` 安装到 `http {}` 上下文，但文件内容是只能位于 `server {}` 内的 `location` 块；
3. DAED 内嵌前端把 GraphQL 地址固定为 `当前主机:2023/graphql`，因此即使 HTML 通过 `/athena-daed/` 打开，浏览器仍会绕过同源代理直连 2023 端口；而 v19 要求 DAED 只监听 `127.0.0.1:2023`，局域网浏览器无法访问该地址。

参考固件的可借鉴原则是：日常管理入口只有一个明确的 Web 服务所有者。v19 不复制参考固件的软件包组合、SmartDNS 或私人配置，只吸收其端口职责清晰、管理入口启动路径简单的做法。

## 2. 已批准的方案

采用方案 A：

- Nginx 是日常管理入口的唯一所有者，独占 80/443；
- uHTTPd 只提供 LAN 恢复入口 `192.168.50.1:8080`；
- DAED 继续只监听 `127.0.0.1:2023`；
- LuCI 中的 DAED 面板通过 Nginx 同源路径 `/athena-daed/` 打开；
- 构建时修正 DAED 前端的 GraphQL 地址，使浏览器访问 `/athena-daed/graphql`，不再直连 2023；
- DAED 默认关闭，DAED 未运行或 eBPF 加载失败时不得影响 LuCI 和恢复入口。

## 3. 目标和验收条件

### 3.1 initramfs 首次启动

在没有持久化 overlay 的情况下，启动完成后必须满足：

- `http://192.168.50.1/` 能跳转或打开正常的 LuCI；
- `https://192.168.50.1/` 能打开 LuCI；
- `http://192.168.50.1:8080/` 能打开恢复 LuCI；
- 80/443 只由 Nginx 监听；
- 8080 只由 uHTTPd 监听；
- 2023 只监听在 `127.0.0.1`，LAN 和 WAN 均不能直接连接；
- DAED 默认关闭，不出现无限重启；
- LuCI 首页和雅典娜图表首页不依赖 DAED 进程。

### 3.2 DAED 启动后

用户配置 DAED 并启动后必须满足：

- `服务 → DAED 面板` 能加载 DAED 原生完整界面；
- HTML、JavaScript、CSS、图片和前端路由都通过 `/athena-daed/` 加载；
- GraphQL HTTP 请求和订阅连接均通过 `/athena-daed/graphql`；
- 浏览器开发者工具中不得出现对 `http(s)://192.168.50.1:2023/` 的请求；
- DAED 后端仍只监听 `127.0.0.1:2023`；
- 页面刷新、DAED 重启和日志流不出现跨域或 WebSocket 失败。

### 3.3 DAED 故障时

若 DAED 未运行、配置错误或 eBPF verifier 拒绝程序：

- LuCI 保持可用；
- DAED 面板显示“未运行”或“启动失败”，不能只显示“已启用”；
- 状态区分别展示 `开机启用`、`进程运行`、`API 可达` 三个状态；
- 页面提供最近的 DAED 错误摘要和诊断命令；
- Nginx 不因上游不可用退出或重启循环；
- 用户可以在 LuCI 或 SSH 中停止 DAED 并恢复普通直连网络。

## 4. Web 服务职责

### 4.1 Nginx：主入口

Nginx 负责：

- 监听 LAN 的 80 和 443；
- 80 跳转到 443；
- 通过现有 `luci-nginx` / uWSGI 栈提供 LuCI；
- 在同一主机和端口下代理 `/athena-daed/`；
- DAED 不可用时返回可识别的 502，由 LuCI 面板转换为清晰状态提示。

Nginx 的启动不能依赖 DAED。DAED 仅是一个可选上游。

### 4.2 uHTTPd：恢复入口

uHTTPd 负责：

- 只监听 `192.168.50.1:8080`；
- 不监听 0.0.0.0:80、`[::]:80`、443 或 WAN 地址；
- 使用 Bootstrap 兼容主题提供最小 LuCI 恢复界面；
- 提供网络、Web 服务、DAED 停止和配置回滚入口；
- 不承担日常访问，不代理 DAED。

为确保 uHTTPd 能实际执行 LuCI，需要在固件配置中包含对应的 uHTTPd Lua 支持，并显式配置 LuCI Lua 前缀。不能只启动一个只会提供静态文件的 uHTTPd 实例。

### 4.3 端口不变量

构建和运行时均强制以下唯一映射：

| 地址/端口 | 唯一服务 | 用途 |
|---|---|---|
| LAN `:80` | Nginx | 跳转主界面 |
| LAN `:443` | Nginx | LuCI 与 DAED 同源入口 |
| `192.168.50.1:8080` | uHTTPd | LAN 恢复入口 |
| `127.0.0.1:2023` | DAED | 本机后端 |

任何其他服务声明上述端口都视为构建或健康检查失败。

## 5. Nginx 同源代理设计

OpenWrt 当前 Nginx 模板将：

- `conf.d/*.conf` 加载到 `http {}` 上下文；
- `conf.d/*.locations` 加载到 LuCI 的 `server {}` 上下文。

因此当前的 `athena-daed.conf` 必须删除，替换为 `athena-daed.locations`。

代理至少提供两个入口：

- `/athena-daed/` → `http://127.0.0.1:2023/`
- `/athena-daed/graphql` → `http://127.0.0.1:2023/graphql`

代理配置必须保留：

- 原始 Host、客户端地址和转发协议头；
- HTTP/1.1；
- WebSocket Upgrade / Connection 头；
- GraphQL 订阅所需的长连接超时；
- 禁用响应缓冲，避免日志与订阅延迟；
- 关闭对后端地址的外部暴露。

不能使用运行时 HTML 字符串替换来修正前端地址，因为压缩、缓存和上游版本变化会使其脆弱。

## 6. DAED 前端构建修复

当前嵌入前端在构建产物中把 GraphQL 端点固定为：

```text
${location.protocol}//${location.hostname}:2023/graphql
```

v19 构建必须在 DAED 前端源码阶段改为同源路径，语义等价于：

```text
${location.origin}/athena-daed/graphql
```

实现要求：

- 优先补丁源文件或构建时环境变量，不直接修改压缩后的随机哈希 JS；
- 前端公共资源 base 为 `/athena-daed/`，或继续使用经验证的相对资源路径；
- 前端路由需要设置 `/athena-daed/` basename，避免导航后跳回 LuCI 根路径；
- 补丁必须绑定到锁定的 DAED/前端提交；
- 若上游源文件结构或目标字符串变化，构建立即失败，禁止静默产出旧行为固件；
- 构建后的二进制扫描不得发现活动代码中的 `:2023/graphql` 浏览器端点。

该修复不改变 DAED 后端的监听协议，也不开放 2023 端口。

## 7. LuCI DAED 面板

LuCI 面板保留 Argon 外层和 DAED 原生完整界面，但加载逻辑改为状态驱动：

1. 查询 DAED 是否设置为开机启用；
2. 查询 DAED 进程是否实际运行；
3. 从路由器本机探测 `127.0.0.1:2023/graphql` 是否可达；
4. 三项都满足后才显示内嵌页面；
5. 任何一项失败时显示状态卡片、最近错误、启动/重试操作和 `athena-health --verbose` 提示。

“enabled” 不能再等同于“running”。对于 eBPF 加载失败后进程退出的情况，页面应明确显示：

- 服务已设置开机启动；
- 进程未运行；
- 后端 API 不可达；
- 最近错误属于 eBPF 加载失败。

面板不得要求局域网直接访问 2023，也不能提供会绕过同源代理的备用链接。

## 8. 首次启动与配置生成

`95-athena-web` 的职责调整为：

- 确认默认 LAN 是 `192.168.50.1/24`；
- 禁止 uHTTPd 默认 main 实例监听 80/443；
- 创建或更新唯一的恢复实例 `192.168.50.1:8080`；
- 确保恢复实例包含可执行 LuCI 的解释器配置；
- 确保 Nginx 主实例启用；
- 将 DAED 监听地址固定为 `127.0.0.1:2023`；
- 保持 DAED 默认关闭；
- 重新加载服务前先做本地配置检查；
- 操作幂等，重复执行不创建重复实例或监听项。

首次启动脚本不得把 Nginx 或 DAED 启动失败隐藏为成功。

## 9. 构建与 CI 验证

### 9.1 源码静态检查

CI 增加：

- 解析 `luci-app-athena.json`，验证 UTF-8 与 JSON 语法；
- 检查 DAED 面板 JavaScript 语法和字符串编码；
- 拒绝裸 `location` 块出现在 `conf.d/*.conf`；
- 要求 DAED 代理使用 `.locations`；
- 验证 uHTTPd 和 Nginx 没有重复端口；
- 验证 DAED 默认关闭且监听 127.0.0.1；
- 验证恢复入口包含真正可用的 LuCI handler；
- 验证前端源码补丁成功应用。

### 9.2 生成配置检查

不能只搜索关键字。CI 必须使用目标 OpenWrt 包生成的配置，至少完成：

- `nginx -t` 等价语法检查；
- 展开后的 Nginx 配置中 `location` 上下文检查；
- uHTTPd UCI 展开后的监听地址检查；
- 端口所有权唯一性检查；
- Web 配置文件权限和启动顺序检查。

若构建环境无法直接运行目标架构 Nginx，则使用 OpenWrt 的配置生成脚本和结构化解析测试，并在真机脚本中补充 `nginx -t`。

### 9.3 固件内容检查

编译后从 initramfs 和 sysupgrade rootfs 中检查：

- 存在 `athena-daed.locations`；
- 不存在旧 `athena-daed.conf`；
- Nginx 主入口和 uHTTPd 恢复入口配置正确；
- DAED 默认配置监听 127.0.0.1；
- 前端产物不再硬编码浏览器访问 `:2023/graphql`；
- uHTTPd LuCI 支持包和 Lua入口存在；
- Argon 和 Bootstrap 回退主题都存在。

### 9.4 真机 initramfs 验证

每次 Release Candidate 必须先在 initramfs 中执行：

- 查看 80、443、8080、2023 的实际监听进程；
- 执行 Nginx 配置测试；
- 分别访问主 LuCI、恢复 LuCI 和 DAED 同源路径；
- 确认 DAED关闭时 LuCI不受影响；
- 启动 DAED 后检查 GraphQL 和 WebSocket；
- 模拟停止 DAED，确认错误页而非白屏；
- 重启一次，验证首次启动脚本幂等；
- 运行 `athena-health --verbose` 并保存结果。

上述 initramfs 验证通过前不得刷写 sysupgrade。

## 10. 健康检查和诊断

`athena-health` 增加 Web 专项检查：

- Nginx 是否运行；
- Nginx 配置是否有效；
- uHTTPd 是否只监听 8080；
- 端口是否被错误进程占用；
- LuCI uWSGI socket 是否存在；
- 本机访问 LuCI 是否返回有效响应；
- DAED enabled/running/API 三态；
- `/athena-daed/` 和 `/athena-daed/graphql` 代理状态；
- DAED 最近是否出现 eBPF verifier、内存或配置错误。

诊断输出必须隐藏 Cookie、Authorization、节点链接、订阅地址和密码。

## 11. 回滚与恢复

运行时配置应用前继续使用 `athena-backup` 备份：

- `/etc/config/nginx`
- `/etc/config/uhttpd`
- `/etc/config/daed`
- `/etc/nginx`
- LuCI 主题设置

`athena-rollback --component web` 应：

- 恢复上述配置；
- 先验证配置再重启服务；
- 保证 8080 恢复入口优先可用；
- DAED 保持停止，直到 Web 管理入口恢复。

initramfs 环境中的修改重启即消失，但仍需支持本次启动内的回滚，以便验证和排障。

## 12. 不在本次修复范围

- 不复制 BleachWrt 的 SmartDNS、代理插件或私人配置；
- 不向 LAN/WAN 开放 DAED 2023；
- 不重写完整 DAED UI；
- 不修改已批准的国内/国外 DNS 与路由策略；
- 不恢复 ECM frontend 或 Flow Offload；
- 不改变 NSS/Wi-Fi offload 策略；
- 不允许在未通过 initramfs 验证前刷写持久化固件。

## 13. 预计修改范围

实现阶段预计涉及：

- `packages/luci-app-athena/root/etc/nginx/conf.d/`
- `packages/luci-app-athena/root/etc/uci-defaults/95-athena-web`
- `packages/luci-app-athena/htdocs/luci-static/resources/view/athena/daed-panel.js`
- `packages/luci-app-athena/root/usr/share/luci/menu.d/luci-app-athena.json`
- DAED 准备/构建脚本及锁定补丁目录
- OpenWrt 包选择配置（补充恢复 uHTTPd LuCI 支持）
- `scripts/verify_web_config.py`
- 固件内容检查、健康检查和真机验证脚本
- README、SETUP、RECOVERY、CHANGELOG 和验证报告

具体文件和测试命令由后续实施计划确定。

## 14. 最终原则

本修复把“服务已启用”“进程正在运行”“Web/API 实际可达”分开判断，并确保管理面与代理数据面解耦：

```text
Nginx/LuCI 可用
    不依赖 DAED

uHTTPd 恢复入口可用
    不依赖 Nginx 或 DAED

DAED 同源面板可用
    依赖 DAED 后端，但不开放 2023
```

任何 DAED 配置或 eBPF 故障都不应再次造成整个路由器管理页面失联。
