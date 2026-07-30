# Athena AX6600 DAED v19.0.0-rc1 仪表盘验证报告

验证日期：2026-07-30  
源码提交：`f670ba8bca295fa3daf7cfd476d92efa61328914`  
分支：`v19-rc1`  
远程操作：未推送 GitHub，未创建 Release

## 已完成的实现

- 新增只读 `athena.dashboard` RPC。
- LuCI“状态 → 概况”和“Athena 优化 → 状态”使用现代化实时仪表盘。
- 本地 SVG 展示 WAN、CPU/内存和 CPU/NSS/Wi-Fi 温度。
- 每 3 秒采样，浏览器最多保存 200 点；刷新页面即清空。
- 增加 DAED eBPF、时间、WAN、DNS、无线和温度告警。
- 页面无外部 CDN、遥测、凭据返回或配置写入。
- 保持 LAN `192.168.50.1`、恢复入口 `192.168.50.1:8080`。
- DAED 默认关闭，仅监听 `127.0.0.1:2023` 并经同源反向代理访问。
- 不内置 SmartDNS；保留 NSS/Wi-Fi offload，停止 ECM frontend 和 Flow Offload。
- 保留独立 2.4 GHz IoT SSID 支持。
- 修复 Feed 中旧 `daed 1.27.0-r1` 覆盖锁定版本的问题，构建必须选择并验证 `2026.07.26-r1`。
- 构建前和构建后均检查仪表盘关键文件。

## 工作树验证

| 验证项 | 结果 |
|---|---:|
| Python 单元/行为测试 | 45/45 通过 |
| Node.js 图表数学测试 | 通过 |
| OpenWrt 运行时 Shell 测试 | 8/8 通过 |
| Shell 语法检查 | 27 个文件通过 |
| 项目结构与不可变源码锁 | 通过 |
| DAED DNS/路由模板 | 通过 |
| 软件包布局 | 通过 |
| Nginx、LuCI、DAED 同源代理与恢复入口 | 通过 |
| 敏感信息扫描 | 通过 |
| `git diff --check` | 通过 |
| 最终 Git 工作树 | 干净 |

执行的验证入口：

```text
python -m unittest discover -s tests -p test_*.py -v
node tests/js/test_dashboard_chart.js
bash scripts/test_runtime_scripts.sh
python scripts/verify_project.py --root .
python scripts/verify_templates.py --templates ... --rules ...
python scripts/verify_package_layout.py --root .
python scripts/verify_web_config.py --root .
python scripts/security_check.py --root .
sh -n <27 个运行时与构建 Shell 文件>
```

## ZIP 解压复验

源码 ZIP 被重新解压到一个新的验证目录，并重复运行：

- Python 45/45；
- Node.js 图表测试；
- 运行时 Shell 8/8；
- 项目、模板、包布局、Web 和安全检查。

以上均通过，证明交付 ZIP 没有遗漏测试、运行时文件或仪表盘资源。

## 交付文件

```text
jdy2-v19.0.0-rc1-dashboard-source.zip
大小：150091 字节
SHA-256：5f1514ebb40f71fa8a9e9928d6dde1cff250de5fa467132532a1c14c13693b3d
```

校验文件：

```text
jdy2-v19.0.0-rc1-dashboard-source.zip.sha256
```

## 尚未完成、不得误报为通过

- 尚未使用这份最终源码重新运行 GitHub Actions 完整固件编译。
- 旧的第 9 次成功构建不包含本次新仪表盘，不能替代新构建。
- 尚未在京东云雅典娜上启动本次最终 initramfs。
- 尚未真机验证 Argon 仪表盘、三路 Wi-Fi、IoT SSID、DAED、NSS 和恢复入口。
- 尚未执行 sysupgrade。

下一次 GitHub Actions 建议参数：

```text
Parallel jobs: 2
Runtime profile: stable
Artifact stage: test
```

构建成功后必须先测试 initramfs。只有 initramfs 的基础网络、无线、DAED、仪表盘、恢复入口和重启检查全部通过，才允许刷写 sysupgrade。

DAED `2026.07.26-r1` 的编译前注册校验与编译后来源校验仍是硬门槛，不应绕过。
