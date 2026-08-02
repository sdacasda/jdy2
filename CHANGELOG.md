# Changelog

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
