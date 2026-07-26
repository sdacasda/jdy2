# Athena v19.0.0-rc1 验证报告

验证日期：2026-07-27

## 输入证据

检查了用户提供的 `Athena-AX6600-v19-5-test.zip`：

- SHA-256：
  `5A15E7D2F3AF671F14DAF93186FD63A46BEF9B2F268D2737D3540C3623A8FB4D`
- `athena-runtime` 已进入合并后的 `tmp/.packageinfo`。
- `luci-app-athena` 没有进入合并后的 `tmp/.packageinfo`。
- `athena-runtime` 已进入实际 `tmp/.config-package.in`。
- 该 Kconfig 符号包含：
  `depends on !(PACKAGE_TAR_XZ) || PACKAGE_xz-utils`。
- 有效配置为 `CONFIG_PACKAGE_TAR_XZ=y`，但
  `CONFIG_PACKAGE_xz-utils` 未选择。

由此确认：

1. `athena-runtime` 在 Kconfig 阶段因 GNU tar 的传递条件被隐藏。
2. `luci-app-athena` 在更早的包扫描阶段因缺少源码扫描签名而丢失。

## 反事实元数据验证

使用锁定的 LiBwrt 源码和第 5 次 Artifact 的完整包元数据，执行了以下验证：

- 删除运行时包的 `+tar +gzip` 后重新生成完整 Kconfig。
- 加入修复后的 LuCI 包元数据。
- 确认 `PACKAGE_athena-runtime` 和 `PACKAGE_luci-app-athena` 均可见。
- 确认运行时包不再带有 `TAR_XZ/xz-utils` 条件。
- 确认 LuCI 包正确选择 `athena-runtime` 与 Web 界面依赖。
- 确认其余平台条件在有效配置中满足：
  Linux 6.12、IPv6、firewall4。

## 测试驱动验证

修复前先加入回归测试并确认它们因以下原因失败：

- LuCI 包缺少 OpenWrt 扫描签名。
- Runtime 包包含多余的 `+tar +gzip` 依赖。
- 诊断脚本对标准 Kconfig 前导空白处理错误。

修复后，上述测试全部通过。

## 已通过

- Python 测试：24/24
- OpenWrt 运行时 Shell 测试：7/7
- 所有项目 Shell 脚本与运行时命令静态语法检查
- 项目结构与不可变源码锁验证
- DAED DNS、路由模板与域名列表验证
- OpenWrt 本地包布局验证
- Nginx、LuCI、DAED 反向代理与恢复入口配置验证
- 敏感信息扫描
- 完整包元数据反事实 Kconfig 验证
- `git diff --check`

## 尚未完成

- Windows 本机不具备 OpenWrt 要求的区分大小写 Linux 文件系统和完整 Ubuntu
  构建环境，因此未执行完整 LiBwrt 固件编译。
- 尚未生成或真机测试新的 initramfs/sysupgrade 镜像。
- GitHub Actions 下一次运行必须确认两个包在 `make defconfig` 后仍为 `y`，
  并继续进入固件编译。

## 下一次 GitHub Actions 验收

使用：

```text
Parallel jobs: 2
Runtime profile: stable
Artifact stage: test
```

预期 `Verify effective OpenWrt config` 通过，并继续执行
`Build both images`。如果仍失败，请下载该次 Artifact；新的包注册诊断会保留
扫描、Kconfig 和有效配置的完整证据。

即使云端编译成功，也必须先从 U-Boot 测试 initramfs。只有基础网络、2.4 GHz
IoT SSID、三路无线、Argon、DAED 面板及恢复入口验证通过后，才考虑刷写
sysupgrade。
