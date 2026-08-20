# DAED 数据库登录修复 — 本地验证报告

日期：2026-08-20
分支：`v19-rc1`
已验证实现快照：`a2a0c5d`（其后的报告提交只更新交付文档）
生产版本元数据：`v19.0.0-rc2`

## 已执行并通过

| 验证 | 结果 |
| --- | --- |
| 完整 Python discovery（进程内加入 bundled Node.js） | `148` 个测试，`0` failure，`0` error，`0` skipped |
| DAED SQLite 补丁、组装与缓存绑定 | `17` 个测试通过 |
| DAED Web 脱敏与完整静态 UI | `21` 个测试通过；Node 行为测试亦在完整矩阵中执行 |
| LuCI、恢复入口与运行时 runner | `15` 个测试通过 |
| 同源 UI、三态语义、nginx 和静态 UI | `35` 个测试通过 |
| 模板删除、包布局与项目验证 | `28` 个测试通过；实际生产/工作流路径无模板接线 |
| 文档与构建脚本 | 包含跨平台 Bash/PATH 与 v19 验证入口回归测试，完整矩阵通过 |
| CI、诊断、安全与来源证明 | `30` 个测试通过 |
| Bash 运行时矩阵 | `11` 个测试，`0` 失败，退出码 `0` |
| POSIX `sh` 运行时矩阵 | `11` 个测试，`0` 失败，退出码 `0` |

完整 Python 命令使用：

```text
C:\Users\mayib\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe
```

并在进程内把 bundled Node.js 目录加入 `PATH`，结果为：

```text
FINAL_PYTHON_TESTS run=148 failures=0 errors=0 skipped=0
```

运行时矩阵通过 Git for Windows 执行：

```text
ATHENA_RUNTIME_TEST_SHELL=bash bash scripts/test_runtime_scripts.sh
ATHENA_RUNTIME_TEST_SHELL=sh sh scripts/test_runtime_scripts.sh
```

两轮均输出：

```text
Runtime tests: 11 run, 0 failed
PASS: all runtime tests
```

## 静态验证

以下命令均退出 `0`：

```text
python scripts/verify_project.py --root .
python scripts/project_check.py --root .
python scripts/verify_package_layout.py --root .
python scripts/verify_web_config.py --root .
python scripts/security_check.py --root .
python -m json.tool PROJECT.json
python -m json.tool SOURCES.lock.json
bash -n scripts/*.sh
git diff --check
```

对应输出包含：

```text
PASS: Athena v19 project structure is valid
PASS: package layout
PASS: web configuration
PASS: no public-source credential patterns found
```

## 配置模板移除核查

发布路径 `packages/**`、`.github/workflows/**` 和生产 shell 脚本中不存在模板/rules 渲染接线，所有退役文件均不在 Git 跟踪列表中。全仓宽泛 grep 仍会命中防回归测试、验证器和历史审计文字；这些字符串用于拒绝模板回归，不是可执行功能。`.superpowers/` 已设置 `export-ignore`，不会进入源码 ZIP。

## 安全与行为结论

- 已验证数据库补丁对未知或部分补丁状态 fail-closed，且不会部分写入。
- 已验证浏览器错误不会渲染密码、GraphQL variables 或序列化异常。
- 已验证恢复流程使用冷备份、校验和、独占锁、严格解析与原服务状态恢复。
- 已验证凭据不经 LuCI/rpcd 传递；恢复仅由 root 交互式 CLI 执行。
- 已验证 DAED 停止时不创建 iframe；运行/API 不可用时仍保留完整同源 UI。
- 已验证浏览器页面不包含 `192.168.50.1:2023`、`127.0.0.1:2023` 或其他直接端口入口。
- 已验证 `collect_output` 测试从 Ubuntu runner 的 `PATH` 解析 Bash，且不会
  把 Windows Git 路径或分隔符写入 POSIX `PATH`。
- 已验证兼容入口 `project_check.py` 使用当前 v19 验证规则，不再读取已删除的
  v18 `athena-final-candidate` 文件。

## 未执行

- 修复后的当前源码提交尚未重新执行 GitHub Actions 完整 LiBwrt 构建：**NOT RUN**。
- 当前源码提交的 initramfs 真机启动、IPv4/IPv6、IoT SSID、NSS/Wi-Fi、DAED 登录恢复验证：**NOT RUN**。
- sysupgrade 持久刷写：**NOT RUN**。

因此本报告证明源码级和本地运行时验证通过，但不会把当前源码称为已经完成真机验收的稳定固件。必须先由 GitHub Actions 成功生成 initramfs 与 sysupgrade，再优先启动 initramfs 完成设备验收。
