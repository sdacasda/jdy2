# Changelog

## v19.0.0-rc2 DAED 登录恢复

- 修复 DAED 首次账户创建的 SQLite 并发初始化，并对登录/设置错误实施脱敏，避免浏览器显示提交的密码或 GraphQL 请求变量。
- 新增认证、确认语句和备份优先的 DAED 密码恢复；恢复前保存 `wing.db` 与 SQLite sidecar，失败时保留备份并尽力恢复原有服务运行状态。
- DAED 继续仅监听 `127.0.0.1:2023`，通过 LuCI 同源 `/athena-daed/` 面板访问；LAN 不能直连端口 2023 是预期安全策略。
- 退役用户配置模板导入流程；内部模板仍随固件提供，`athena-setup` 不再要求用户导入。

## v19.0.0-rc1 IPv6 与 DAED 状态修复

- 首页同时读取 `network.interface.wan` 与独立的 `network.interface.wan6`，可识别 `wan6` 上的 IPv6 地址或下发前缀，不再把有效双栈连接误报为“IPv6 未连接”。
- DAED 完整原生 UI 仅在 `daed` 进程停止时隐藏；进程运行时始终嵌入同源 `/athena-daed/`，GraphQL 业务状态由原生界面自行展示。
- DAED GraphQL 探针在 BusyBox `wget` 不支持 POST 参数或请求失败时继续使用本地 `nc` 探针，不再提前返回错误状态。
- 继续禁止浏览器直接访问 LAN `:2023`；`192.168.50.1:2023` 返回连接拒绝是 loopback-only 安全策略的预期结果。

## v19.0.0-rc1 原生 DAED UI 与主页修复

- 修复现代化主页的 LuCI 模块契约：`athena.chart` 现在返回可实例化的 `L.Class` 子类，不再触发 `factory yields invalid constructor`。
- 完整 DAED 原生 UI 从与 DAED 二进制相同的固定源码归档提取，静态提供在 `/athena-daed/`；即使 DAED 默认关闭或 eBPF 加载失败，HTML/CSS/JavaScript 界面仍可打开。
- 只有 `/athena-daed/graphql` 反向代理到 `127.0.0.1:2023/graphql`，浏览器不会直接访问或暴露 2023 端口。
- LuCI 的“DAED 面板”仅在进程与 GraphQL API 均就绪时嵌入完整原生界面；核心停止或后端不可达时仅显示“后端未连接”。
- DAED API 健康探针改为 GraphQL POST，并将合法的 GraphQL `errors` 响应识别为“后端已连接”，避免把缺少节点等业务错误误报为 API 不可达。
- 源码缓存与固件检查现在绑定完整静态 UI 的文件清单、大小、SHA-256 和树摘要，并拒绝缺少 JS、CSS、logo、错误端点或整站代理的产物。
- GitHub Actions 在约四小时固件编译前检查静态 UI 和 provenance，安装器逻辑变化也会使 DAED 源码缓存失效。
- 保持 DAED 默认关闭、仅监听回环地址，保留 Argon 深色主题配置、8080 恢复入口和原有网络/IoT/NSS/ECM 策略。

## v19.0.0-rc1 第 13 次构建检查修复

- 第 13 次 GitHub Actions 已成功组装固定来源的 DAED、完成双镜像编译并生成 initramfs 与 sysupgrade；失败仅发生在最后的固件离线检查。
- 修复检查器对 DAED ELF 内 gzip 嵌入前端的误判：现在会有界解压嵌入资源并验证同源 `/athena-daed/graphql`。
- 保留反向安全门槛：即使 `:2023/graphql` 隐藏在 gzip 资源中，检查器仍会拒绝该镜像。
- 关闭 `actions/setup-go` 无效的仓库根目录模块缓存，消除“找不到根目录 go.mod”的非致命警告；DAED 校验型源码缓存不受影响。

## v19.0.0-rc1 DAED 源码耐久性修复

- 修复第 12 次构建中 `daed-src-2026.07.26-ecbc5c99d632.tar.gz` 上游 Release 资产返回 404，导致完整编译结束后无 initramfs 的问题。
- CI 现在从上游 `ci/pins.env` 中的不可变组件提交本地组装 DAED 源码，不再依赖只保留少量历史文件的 Release 下载地址。
- 使用 Go 1.26.0、Node.js 24 和锁定的 pnpm workspace 构建 DAED Web，并在前端编译前应用同源 `/athena-daed/graphql` 修补。
- 组装包采用规范化时间、排序、属主和 `gzip -n`，实际 SHA-256 自动写入本次 OpenWrt 包定义。
- 完整固件编译前单独执行 `package/daed/download`，先验证本地源码包存在且校验通过，避免再次浪费数小时。
- 缓存归档必须匹配全部组件 pins、assembly manifest、SHA-256 和已编译的同源 Web 端点，否则自动重建。
- DAED 下载预检成功后立即保存源码缓存，即使后续固件编译失败也能用于下一次重试。
- Artifact 新增 `diagnostics/daed-source-provenance/`，保存组件 pins、源码包哈希和 OpenWrt 下载验证日志。

## v19.0.0-rc1 Web/DAED 修复

- 修复 Nginx 与 uHTTPd 同时占用主 Web 端口的问题：Nginx 独占 80/443，uHTTPd 只提供 `192.168.50.1:8080` 恢复入口。
- 将 DAED 代理从错误的 `conf.d/*.conf` 改为服务器上下文中的 `*.locations`。
- 构建时精确修补 DAED 前端 GraphQL 地址为同源 `/athena-daed/graphql`，上游布局变化时立即失败。
- DAED 面板新增“开机启用、进程运行、API 可达”三态显示和启动/停止/重试操作。
- eBPF、配置、内存和不可用错误只返回脱敏分类，不泄露节点或日志内容。
- 新增 Web 端口、Nginx、恢复页面和 DAED API 健康检查。
- 新增 `athena-rollback --component web`，仅恢复 Web/服务配置，不修改 `wing.db`。
- 固件检查新增同源 DAED 端点、恢复页面、uHTTPd Lua、旧 Nginx 文件和默认监听策略门槛。
- 真机验证脚本新增主 LuCI、恢复入口、DAED 隔离与同源 GraphQL 检查。
- 修复用户文档中文编码。

## v19.0.0-rc1 基础功能

- LAN 改为 `192.168.50.1`。
- DAED 默认关闭且只监听回环地址。
- Argon 深色主题默认启用，Bootstrap 保留。
- 新增现代化图表首页、运行时工具、DNS/路由模板、游戏与 BT 分流模板。
- 新增可选独立 2.4 GHz IoT SSID。
- 保留 NSS/Wi-Fi offload，停止 ECM frontend 与 Flow Offload。
- 外部源码全部锁定，固件双镜像与 6 MiB 内核槽强制检查。

## v18

- 增加 WOL、DAED、外置 BTF、雅典娜屏幕及双镜像构建。
