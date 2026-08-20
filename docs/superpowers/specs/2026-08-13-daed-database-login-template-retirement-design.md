# Athena v19 DAED 数据库登录修复与配置模板退役设计

日期：2026-08-13
状态：用户已批准设计，等待书面规范复核

## 1. 背景与证据

设备日志表明 dae 数据面已经完成 eBPF 加载、路由构建并进入 `Ready`。故障发生在 DAED 管理平面：

- 首次账户初始化和配置重载期间出现 `SQLITE_BUSY`、`database is locked`；
- 用户、路由、节点组和系统状态查询随后持续超时；
- Web 登录出现 `cannot start a transaction within a transaction`；
- 登录失败提示序列化了完整 GraphQL 请求对象，导致用户名和密码出现在浏览器中；
- LuCI 中的“配置模板”页面为空，并与完整 DAED UI 的配置功能重复。

`Athena-AX6600-v19-20-test.zip` 仅含源码验证失败诊断，没有 initramfs 或 sysupgrade，不能作为可刷写固件。第 20 次工作流运行编号也不是固件版本号。

## 2. 目标

1. 保留现有 DAED 节点、订阅、DNS、路由和账户数据库数据。
2. 修复首次账户创建和配置重载期间的 SQLite 并发与事务错误。
3. 登录失败时只显示安全、最小的错误文本，绝不显示请求变量或密码。
4. 提供经过确认、先备份后执行的 DAED 密码恢复入口。
5. 完整退役“配置模板”用户工作流。
6. 保持完整 DAED UI 通过 `/athena-daed/` 同源嵌入 LuCI。
7. 保持 DAED 默认关闭、仅监听 `127.0.0.1:2023`，不向 LAN 暴露 2023 端口。

## 3. 非目标

- 不删除、重建或自动清空 `wing.db`。
- 不自动导入 DNS、路由或节点配置。
- 不恢复 SmartDNS。
- 不修改 dae 的代理、NSS、Wi-Fi offload 或 ECM 策略。
- 不把 DAED 密码写入 UCI、日志、浏览器存储或构建产物。

## 4. 设计方案

### 4.1 固定源码层的 SQLite 修复

构建流程继续从锁定提交组装 DAED/dae-wing，并在编译前对固定源码应用可审计补丁：

- SQLite 连接池限制为一个活动连接和一个空闲连接，避免同一数据库上的并发写事务；
- 设置明确的 `busy_timeout`，短暂占用时等待而非立即失败；
- `CreateUser` 在执行查询前检查 `Begin` 是否成功；
- 提交失败必须通过命名返回错误上送，回滚路径不得吞掉原始业务错误；
- 补丁只接受已知的锁定源码布局，锚点不匹配时构建失败，不做模糊替换。

补丁哈希必须进入 DAED 源码缓存键和 provenance。CI 必须验证最终组装源码包含补丁，不能只验证补丁脚本本身。

### 4.2 登录错误脱敏

DAED Web 的登录与首次管理员创建页面只从 GraphQL `response.errors[].message` 提取文本。其他异常统一显示 `DAED request failed`。

禁止显示或记录：

- GraphQL `request`；
- `variables`；
- username/password 输入；
- `ClientError.message` 的完整序列化内容；
- `JSON.stringify(error)` 的结果。

同源 GraphQL 入口保持 `/athena-daed/graphql`，浏览器不得直接连接 `:2023`。

### 4.3 保留数据的密码恢复

LuCI DAED 面板增加“重置 DAED 密码”，并提供 SSH 命令 `athena-daed-reset-password`。恢复流程：

1. 要求精确确认语句 `RESET DAED PASSWORD`；
2. 获取互斥锁，避免同时执行多个恢复任务；
3. 在任何数据库写入前，冷备份 `wing.db` 以及存在的 `-wal`、`-shm`、`-journal`；
4. 为备份生成 SHA-256 清单并立即验证；
5. 停止 DAED，并同时确认进程和 GraphQL 入口均已停止；
6. 执行锁定版本提供的 `daed resetpass --config /etc/daed`；
7. 严格解析唯一一行账号和随机密码结果；
8. 仅在一次性结果对话框或 CLI 标准输出中返回凭据；
9. 恢复操作前的运行状态，失败时保留备份和可诊断错误。

密码恢复只修改账户密码，不删除节点、订阅、DNS、路由或组。若数据库结构损坏到无法恢复，工具必须停止并保留备份；全新初始化只能由用户在看到明确的数据丢失警告后另行决定。

### 4.4 配置模板彻底退役

删除以下内容：

- LuCI“配置模板”菜单和 `templates.js`；
- rpcd `templates` 方法及 ACL；
- `templates.sh` 模板渲染器；
- `/usr/share/athena/templates/`；
- 仅为模板生成服务的 Steam/Xbox 域名清单和规则资源；
- `verify_templates.py`、模板单元测试及工作流调用；
- 文档中的手工导入流程和 `generated/*.dae` 引用。

`athena-setup` 只执行环境预检、备份、运行时策略应用和严格健康检查，不等待模板导入，也不直接修改 `wing.db`。

### 4.5 LuCI 行为

DAED 面板保留三项独立状态：开机启用、进程运行、API 可达。

- 进程未运行：显示“后端未连接”，不加载 iframe；
- 进程运行但 API 不可达：仍加载完整 DAED UI，同时显示数据库/API 故障提示和密码恢复入口；
- API 可达：正常显示完整 DAED UI；
- 绝不使用 `192.168.50.1:2023` 作为浏览器入口。

这能区分“核心停止”和“管理数据库损坏”，避免把正在运行但 API 锁死的 DAED误报为完全关闭。

## 5. 数据和安全边界

- `wing.db` 及其备份权限为仅 root 可读写；备份目录仅 root 可访问。
- 密码不得持久化，不得写入日志、UCI、URL、文件或 Web Storage。
- 恢复 RPC 只能由已认证且拥有 `luci-app-athena` 写权限的 LuCI 会话调用。
- 截图中已经出现的密码视为泄露；用户应更换该密码及所有复用位置的密码。
- 构建安全扫描继续拒绝真实节点链接、订阅令牌、UUID、私钥和密码。

## 6. 测试与构建门槛

必须先添加失败回归测试，再修改生产代码。

### 6.1 数据库补丁

- 固定源码哈希与锚点校验；
- 连接池串行化和 `busy_timeout`；
- `Begin`、`Commit`、`Rollback` 错误路径；
- 重复执行补丁幂等；
- 未知上游布局拒绝且不产生部分写入；
- 补丁哈希进入组装缓存与 provenance。

### 6.2 Web 脱敏

- 代表性 `ClientError` 中放入哨兵密码；
- 断言页面只返回 GraphQL message；
- 断言构建后的前端不包含哨兵密码、完整请求输出或直接错误序列化；
- 同源 `/athena-daed/graphql` 保持有效。

### 6.3 密码恢复

- 错误确认语句没有副作用；
- 数据库及 sidecar 备份完整且校验通过；
- DAED 无法停止时不得执行 `resetpass`；
- 重置失败时服务状态恢复、备份保留；
- 成功时凭据只出现一次且不落盘；
- 并发、信号中断和异常输出均安全失败；
- 不支持把专用恢复目录误交给普通 `athena-rollback`。

### 6.4 模板退役

- 菜单、ACL、RPC、页面、渲染器、模板资源及 CI 调用全部不存在；
- `athena-setup` 不引用模板或生成目录；
- 文档不再要求用户导入模板。

### 6.5 完整验证

- Python 单元测试；
- JavaScript 测试；
- Bash 主机运行时测试；
- 所有生产 shell 文件用 dash 做语法检查；
- 项目结构、Web 配置、安全扫描和 DAED provenance 检查；
- GitHub Actions 必须生成真实 initramfs 与 sysupgrade，失败诊断 Artifact 不得标记为固件。

## 7. 交付与迁移

目标源码目录为 `E:\Users\mayib\Desktop\jd`。实现与验证先在可写工作区完成，最后复制经过验证的完整源码、源码 ZIP、SHA256、变更摘要和验证报告到该目录。

新固件仍先用 initramfs RAM 启动验证。验收项目包括：

- DAED 首次创建管理员不再产生嵌套事务或数据库锁；
- 错误提示不泄露密码；
- 旧 `wing.db` 的节点与配置仍存在；
- 密码恢复可用；
- “配置模板”入口完全消失；
- DAED UI 继续在 LuCI 中完整嵌入；
- `192.168.50.1:2023` 仍拒绝连接，这是预期安全行为。

只有真机 initramfs 验证通过后，才允许生成候选发布说明；不会自动推送 GitHub。
