# DAED 数据库登录修复 — 变更摘要

日期：2026-08-20
版本元数据：`v19.0.0-rc2`

本次源码交付针对用户实测的 DAED SQL 事务冲突、登录失败、错误信息泄露密码、LuCI 状态误判，以及已经不再需要的“配置模板”页面进行了完整收敛。

## 主要修复

- 在不可变、锁定的 DAED 源码组装阶段应用 SQLite 修复：限制为一个打开/空闲连接，设置 10 秒 `busy_timeout`，并让事务开始与提交错误正确返回。
- DAED Web 登录/初始化错误只展示 GraphQL 的安全消息；请求变量、密码、序列化异常和内部请求体不会进入浏览器提示。
- 密码恢复统一使用 root 交互命令 `athena-daed-reset-password`：要求精确确认短语、独占锁、停服验证、数据库及 sidecar 冷备份和 SHA-256 校验；临时凭据只显示一次，不写入 UCI、日志、rpcd 或浏览器状态。
- 完整原生 DAED UI 继续通过同源 `/athena-daed/` 嵌入 LuCI；浏览器不访问 `:2023`。DAED 停止时仅显示“后端未连接”，进程运行但 API 异常时仍保留完整 UI 并显示警告。
- 完全移除配置模板子系统，包括 LuCI 页面、模板/规则文件、渲染器、rpcd/ACL、CI 调用和用户导入说明；订阅、节点、DNS 和路由直接在原生 DAED UI 管理。
- CI 对所有必要阶段 fail-closed；不完整构建只输出诊断，不伪装成固件 Artifact。DAED 数据库补丁、Web 补丁、静态 UI 和最终包均绑定来源证明。
- 安全扫描覆盖代理链接、Token、私钥、UUID、GraphQL 密码变量和已知哨兵凭据。
- 修复 Windows 本地测试的 UTF-8 解码问题，并让源码 ZIP 排除 `.superpowers/` 内部工作产物。

## 保持不变的安全默认值

- LAN：`192.168.50.1`
- DAED：默认关闭，仅监听 `127.0.0.1:2023`
- 浏览器入口：同源 `/athena-daed/`
- SmartDNS：不内置
- NSS/Wi-Fi offload：保留
- ECM frontend 与软件/硬件 flow offload：按既定 Athena 运行时策略停止
- 单独 IoT SSID：功能保留，默认关闭

完整执行证据和未执行项目见 `VERIFICATION_REPORT-v19-daed-database-login-fix.md`。
