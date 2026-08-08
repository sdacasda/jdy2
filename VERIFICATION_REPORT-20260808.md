# Athena v19.0.0-rc1 验证报告

日期：2026-08-08
范围：源码、模板、运行时脚本、LuCI/Nginx 集成、Artifact 与固件离线检查逻辑。

## 已通过

| 验证项 | 结果 |
|---|---:|
| Python 自动化测试 | 72 项通过，0 失败 |
| OpenWrt/BusyBox 运行时测试 | 9 组通过，0 失败 |
| 仪表盘图表计算 | 通过 |
| DAED 模板与规则结构 | 通过 |
| 本地包布局 | 通过 |
| 项目结构 | 通过 |
| Nginx/uHTTPd/DAED Web 配置 | 通过 |
| 凭据与代理链接安全扫描 | 通过 |
| Python/Shell/JavaScript 语法 | 通过 |
| Git 空白与补丁格式检查 | 通过 |
| 中文文档 UTF-8 与乱码回归 | 通过 |
| DAED 本地源码安装、哈希固定与工作流顺序 | 通过 |

测试覆盖的关键不变量：

- Nginx 是 80/443 唯一所有者；uHTTPd 只使用 `192.168.50.1:8080`。
- 不存在旧 `athena-daed.conf`，DAED 代理只通过 `athena-daed.locations` 加载。
- DAED 浏览器端 GraphQL 使用 `/athena-daed/graphql`，不直接访问 2023。
- DAED 默认关闭且只绑定 `127.0.0.1:2023`。
- eBPF 失败时 LuCI 与恢复入口仍独立可用。
- 固件离线检查会拒绝缺失恢复页面、Lua LuCI、同源代理或错误监听的镜像。
- SmartDNS、OpenClash、PassWall 与 HomeProxy 未加入默认固件配置。

## 验证过程中发现并修复

独立执行验证器时发现 `scripts/verify_package_layout.py` 仍要求已经删除的 `athena-daed.conf`。该检查器及测试夹具已改为要求 `athena-daed.locations`，随后独立测试和完整测试均通过。

第 12 次 GitHub Actions 诊断包确认：上游 DAED Release 源码资产返回 404，导致 `package/custom/daed` 失败并最终没有生成 initramfs。源码现改为从不可变组件提交本地组装；单元测试验证本地归档复制、SHA-256 写回、组件提交校验、前端修补顺序、缓存 manifest/嵌入 Web 校验、失败后缓存保留和 CI 下载前置门槛。完整 DAED 组装及 LiBwrt 固件编译仍需下一次 Ubuntu/GitHub Actions 运行验证。

## 未执行/未证明

| 项目 | 状态 | 原因与下一步 |
|---|---|---|
| 完整 LiBwrt/OpenWrt 编译 | 未在本机执行 | 需要 Ubuntu/GitHub Actions 工具链；上传源码后运行 `stable/test` 构建 |
| 实际 initramfs 启动 | 未执行 | 使用新 Artifact 从 U‑Boot RAM 启动验证 |
| DAED eBPF 真机加载 | 未执行 | 启用 DAED 后确认无 `LocalTcpSockops`/`bpf_get_current_task#35` FATAL |
| 三路 Wi‑Fi 与 IoT 设备接入 | 未执行 | 真机逐一检查 PHY，并测试独立 WPA2 2.4 GHz IoT SSID |
| sysupgrade 持久刷写 | 禁止 | 只有 initramfs 全部门槛通过后才能考虑 |

## 真机验收顺序

1. GitHub Actions 选择 `Parallel jobs=2`、`Runtime profile=stable`、`Artifact stage=test`。
2. 校验 Artifact 内 SHA256 与 DAED provenance 文件。
3. 只用 U‑Boot 启动 initramfs，不写闪存。
4. 验证 `https://192.168.50.1/` 和 `http://192.168.50.1:8080/`。
5. 验证 Argon、现代仪表盘、三路 Wi‑Fi、IoT SSID、WAN 与 DNS。
6. 导入配置后启用 DAED，确认进程和 GraphQL API 均可用且无 eBPF FATAL。
7. 运行 Artifact 中的 `tools/verify-after-flash.sh`。
8. 仅在所有关键项通过后，才考虑 `sysupgrade -n`。
