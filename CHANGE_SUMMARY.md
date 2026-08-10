# Athena v19.0.0-rc1 变更摘要

日期：2026-08-09

## 本次交付：主页与完整 DAED 原生 UI

- 主页错误的根因是 `athena/chart.js` 返回普通对象，而 LuCI 的 `'require athena.chart'` 需要可实例化的类。模块现返回标准 `L.Class` 子类，现有采样、CPU、速率和 SVG 计算 API 保持不变。
- `/athena-daed/` 现在由 Nginx 从 `/www/athena-daed/` 静态提供完整原生 DAED SPA；该目录来自本次固定 DAED 源码归档中的 `apps/web/dist`，不是独立下载或维护的第二套 UI。
- `/athena-daed/graphql` 是唯一代理到 `127.0.0.1:2023/graphql` 的路径。静态 UI 不依赖 DAED 进程提供 HTML/CSS/JavaScript，直接访问 `192.168.50.1:2023` 仍应被拒绝。
- LuCI 面板仅在 DAED 进程与 GraphQL API 都就绪时显示完整原生 iframe；后端未连接时只显示“后端未连接”。GraphQL 业务错误仍被正确识别为 API 已连接。
- 安装器安全拒绝路径穿越、链接、缺失引用、浏览器可见 2023 和非同源 GraphQL；缓存、CI 和固件检查继续验证整棵静态资源树。

这项修改明确不解决内核自身的 eBPF helper 兼容性；它保证后端失败不会连带让 DAED 管理 UI 消失。

## 第 13 次构建结论

第 13 次运行已证明固定来源 DAED 的本地组装、OpenWrt 双镜像编译和 DAED provenance 校验全部成功。Artifact 中同时存在 initramfs 与 sysupgrade，内核为 5,561,400 字节，距离 6 MiB 上限仍有 730,056 字节；包清单、禁用包和仪表盘文件检查也全部通过。

唯一失败来自离线检查器直接在 DAED ELF 中搜索 `/athena-daed/graphql`。DAED 组装流程会把较大的 Web 文件 gzip 压缩后再嵌入 ELF，因此字符串并非明文存在。检查器现已改为有界扫描有效 gzip 成员，既能识别同源端点，也能继续拦截压缩资源内的 `:2023/graphql`。

同时关闭了 `setup-go` 在仓库根目录寻找 `go.mod` 的内置缓存探测；项目自己的 DAED 源码缓存继续使用，不会增加重复组装时间。

## 第 12 次构建修复

第 12 次构建的主要错误不是镜像收集，而是锁定 DAED Makefile 引用的 Release 源码包已经被上游删除，下载返回 404；`Expected one initramfs, found 0` 是该编译失败的后续表现。

新流程在完整 OpenWrt 编译前，从锁定 DAED 仓库携带的组件 pins 重新组装源码包，并先运行 `package/daed/download` 验证。DAED Web 同源地址也改为在前端构建前修补，确保修补真正进入嵌入式页面。源码包组件提交、SHA-256、组装日志和下载检查日志都会进入诊断 Artifact。

## 本次修复目标

修复 initramfs 内存启动时 LuCI 与 DAED 页面不可用的问题，同时确保 DAED eBPF 启动失败不会拖垮管理界面或恢复入口。

## Web 架构

- Nginx 独占 80/443，提供 LuCI、Argon 与 DAED 同源入口。
- uHTTPd 不再占用主 Web 端口，只绑定 `192.168.50.1:8080` 作为 LAN 恢复入口。
- 删除不能在 Nginx `http {}` 上下文直接加载的 `athena-daed.conf`，改为服务器上下文加载的 `athena-daed.locations`。
- DAED 只监听 `127.0.0.1:2023`；浏览器静态加载 `/athena-daed/`，只有 `/athena-daed/graphql` 访问回环后端。
- 构建时精确修补并提取 DAED 原生前端；上游源码结构变化、资源缺失或摘要变化时立即失败，避免生成半损坏页面。

## DAED 状态与恢复

- DAED 面板区分“开机启用、进程运行、API 可用”三种状态。
- eBPF、配置、内存和不可用错误会分类显示，敏感日志不会返回浏览器。
- 无论进程与 API 状态如何都加载 DAED 原生页面；后端不可用时保留状态提示。
- 新增启动、停止、重试操作和相应 RPC 权限。
- `athena-health` 增加 Nginx、端口所有权、8080 恢复入口、DAED 进程/API 检查。
- `athena-rollback --component web` 可仅恢复 Web 与服务配置，不修改 `wing.db`。

## 构建与防回归

- 固件检查新增 `uhttpd-mod-lua`、同源 DAED、恢复页面、默认监听与旧 Nginx 文件门槛。
- 真机验证脚本检查 LuCI、8080、DAED loopback、同源 GraphQL、NSS/ECM/Flow Offload 状态。
- 修正包布局验证器，使其与新的 `.locations` 架构一致。
- 重写全部面向用户的中文文档为 UTF‑8，并新增乱码回归测试。

## 保持不变的安全默认值

- LAN：`192.168.50.1/24`。
- DAED 默认关闭，仅 loopback 监听。
- Argon 默认深色且保留主题配置；Bootstrap 用于恢复。
- 不内置 SmartDNS。
- 国内直连、国外代理；国内 UDP DNS、国外代理 DoH、节点 bootstrap 直连。
- Steam 下载、游戏与 BT 选择性直连。
- NSS/Wi‑Fi offload 保留；ECM frontend 与 Flow Offload 停止。
- 独立 2.4 GHz IoT SSID 默认关闭，按需运行 `athena-iot setup`。

## 仍需外部验证

- 本地 Windows 环境未执行完整 LiBwrt/OpenWrt 编译。
- 未在 RE-CS-02 上运行新 initramfs。
- 锁定 DAED 的 eBPF 兼容性必须以新 GitHub Actions Artifact 和真机日志为准。
- 通过 initramfs 验证前禁止刷写 sysupgrade。
