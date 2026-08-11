# Athena v19.0.0-rc1 验证报告

## 2026-08-11 增量验证

- 新增 `wan` 无 IPv6、`wan6` 有 IPv6 地址/前缀的回归用例，修复前失败、修复后通过。
- 新增 BusyBox `wget` POST 不可用、`nc` 本地 GraphQL 响应成功的回归用例，修复前失败、修复后通过。
- 新增 LuCI DAED 面板只按进程状态控制完整 iframe 的回归断言，修复前失败、修复后通过。
- 完整本地静态与单元测试结果见 `IPV6_DAED_STATUS_FIX_VALIDATION.md`；完整固件编译和 RE-CS-02 initramfs 真机复测仍需 GitHub Actions 与设备完成。

日期：2026-08-09
范围：主页 LuCI 模块、固定来源 DAED 静态 UI、Nginx/GraphQL 分流、源码缓存、固件离线检查、CI 前置门槛和既有 v19 功能回归。

## 本地验证结果

| 命令/项目 | 结果 |
|---|---:|
| `bash -n scripts/assemble_daed_source.sh` | 通过 |
| `node tests/js/test_dashboard_chart.js` | 通过 |
| Python 关键脚本 `py_compile` | 通过 |
| `python -m unittest discover -s tests -p 'test_*.py' -v` | 111 项通过，0 失败，9.371 秒 |
| `bash scripts/test_runtime_scripts.sh` | 9 组通过，0 失败 |
| `verify_project.py` | 通过 |
| `verify_templates.py` | 通过 |
| `verify_package_layout.py` | 通过 |
| `verify_web_config.py` | 通过 |
| `security_check.py` | 通过 |
| `git diff --check` | 通过 |

端点搜索仅发现预期的回环 GraphQL 代理/健康检查，以及用于拒绝危险配置的验证器常量；LuCI iframe 和静态 DAED 浏览器资源中没有 LAN 可见的 `:2023` 地址。

## 已验证的不变量

- `athena/chart.js` 返回可实例化的 LuCI `L.Class` 子类，现有图表计算方法保持可调用。
- `/athena-daed/` 从 `/www/athena-daed/` 静态提供完整 DAED 原生 SPA，不代理整站。
- 只有 `/athena-daed/graphql` 代理到 `127.0.0.1:2023/graphql`。
- LuCI 仅在 DAED 进程与 GraphQL API 都就绪时创建同源 `/athena-daed/` iframe；停止或不可达时仅显示“后端未连接”。
- iframe 允许原生 UI 所需的脚本、表单、弹窗、下载和剪贴板功能，但不注入或改写 DAED UI。
- 静态 UI 来自与 DAED 二进制相同的固定源码归档；安全安装器拒绝路径穿越、链接、缺失引用、浏览器 2023 端口和非同源 GraphQL。
- 缓存 manifest 绑定完整静态 UI 文件清单、大小、SHA-256 和树摘要；旧 schema 或任一资源变化都会拒绝缓存。
- 固件离线检查复算固件内每个静态资源的大小、SHA-256 和树摘要，并拒绝缺失/额外文件、错误引用、整站代理或非回环 GraphQL。
- GitHub Actions 的 DAED 源码缓存键包含静态 UI 安装器，且在长时间固件编译前检查静态 UI、包内 manifest 和外部 provenance。
- DAED 仍默认关闭并只监听 `127.0.0.1:2023`；uHTTPd 恢复入口仍为 LAN `192.168.50.1:8080`。
- LAN `192.168.50.1/24`、Argon、IoT SSID、DNS/路由、Steam/游戏/BT、IPv6、NSS、ECM 和 Flow Offload 策略未被本次改动调整。

## TDD 证据

本次新回归用例均先在旧实现上观察到失败，再实现最小修复：

- 主页模块测试最初收到普通对象而非构造函数。
- Nginx 测试最初发现 `/athena-daed/` 仍整站代理。
- LuCI 新回归测试最初发现未就绪状态仍无条件创建 iframe。
- API 回归测试最初发现合法 GraphQL `errors` 响应被旧 HTTP GET 探针误报为不可达。
- 固件检查负向夹具最初错误接受缺少静态资源、危险端点和错误代理。
- 工作流测试最初发现缓存键和长编译前门槛未包含静态 UI。

## 尚未执行/不能由本机证明

| 项目 | 状态 | 下一步 |
|---|---|---|
| 本次源码的完整 LiBwrt/OpenWrt 编译 | 未执行 | 上传源码后运行 GitHub Actions `stable/test` |
| DAED 来源缓存命中构建 | 未执行 | 首次成功构建后再次运行，确认 manifest 复验路径 |
| RE-CS-02 initramfs 启动 | 未执行 | 仅从 U-Boot RAM 启动新 initramfs |
| 主页浏览器渲染 | 未执行 | 确认不再出现 `athena.chart factory yields invalid constructor` |
| DAED 停止时完整 UI | 未执行 | 确认原生状态/订阅/节点组/DNS/路由/设置/日志页面可加载 |
| DAED 启动后的 GraphQL 重连 | 未执行 | 启动服务后确认原生 UI 恢复实时数据 |
| eBPF 真机兼容性 | 未解决/未验证 | 本次只保证 UI 独立；仍需检查 `LocalTcpSockops` 日志 |
| LAN/WAN 对 2023 端口隔离 | 未真机验证 | LAN 与 WAN 均不得直接访问，只有路由器 loopback 可用 |
| 8080 恢复入口 | 未真机验证 | 确认 `http://192.168.50.1:8080/` 可用 |
| sysupgrade 持久刷写 | 禁止 | initramfs 全部门槛通过后才考虑 |

## 真机验收顺序

1. GitHub Actions 使用 `Parallel jobs=2`、`Runtime profile=stable`、`Artifact stage=test`。
2. 确认构建、DAED provenance、固件检查和 Artifact 上传全部成功。
3. 校验 Artifact 中 SHA-256，只用 U-Boot 启动 initramfs，不写闪存。
4. 验证 Argon 主页和动态图表，确认浏览器控制台无 `invalid constructor`。
5. 在 DAED 保持关闭时进入“服务 → DAED 面板”，确认只显示“后端未连接”，且不创建原生 UI iframe。
6. 启动 DAED，确认 `/athena-daed/graphql` 恢复数据并显示完整原生 UI，同时直接 `192.168.50.1:2023` 仍拒绝连接。
7. 检查 eBPF、三路 Wi-Fi、独立 2.4 GHz IoT SSID、WAN、DNS、NSS/ECM/Flow Offload 和 8080 恢复入口。
8. 运行 Artifact 中的 `tools/verify-after-flash.sh`。
9. 只有全部关键项通过后，才评估 `sysupgrade -n`。
